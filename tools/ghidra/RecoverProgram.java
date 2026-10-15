// Private, resumable static recovery export. Never executes the imported program.
//@category MotorCity.Recovery
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.data.*;
import com.google.gson.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.io.*;
import java.util.*;

public class RecoverProgram extends GhidraScript {
    private final Gson gson = new Gson();
    private JsonObject object() { return new JsonObject(); }
    private void save(Path path, String value) throws IOException {
        Path temporary = path.resolveSibling(path.getFileName() + ".tmp");
        Files.writeString(temporary, value, StandardCharsets.UTF_8);
        Files.move(temporary, path, StandardCopyOption.REPLACE_EXISTING);
    }
    private String address(Function function) { return function.getEntryPoint().toString(); }
    private JsonObject identity(Function f) {
        JsonObject row = object();
        row.addProperty("address", address(f));
        row.addProperty("name", f.getName(true));
        row.addProperty("external", f.isExternal());
        row.addProperty("thunk", f.isThunk());
        row.addProperty("body_bytes", f.getBody().getNumAddresses());
        row.addProperty("signature", f.getSignature().toString());
        row.addProperty("calling_convention", f.getCallingConventionName());
        JsonArray calls = new JsonArray();
        TreeSet<String> targets = new TreeSet<>();
        for (Function called : f.getCalledFunctions(monitor)) targets.add(address(called));
        for (String target : targets) calls.add(target);
        row.add("direct_callees", calls);
        return row;
    }
    @Override public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 5) throw new IllegalArgumentException("output max-functions timeout-seconds retry-failed run-id required");
        Path output = Paths.get(args[0]);
        int limit = Integer.parseInt(args[1]);
        int seconds = Integer.parseInt(args[2]);
        boolean retry = Boolean.parseBoolean(args[3]);
        boolean retryTimeouts = "timeouts".equals(args[3]);
        Files.createDirectories(output.resolve("pseudocode"));
        JsonObject metadata = object();
        metadata.addProperty("schema_version", 1);
        metadata.addProperty("target_sha256", currentProgram.getExecutableSHA256());
        metadata.addProperty("program", currentProgram.getName());
        metadata.addProperty("language", currentProgram.getLanguageID().toString());
        metadata.addProperty("compiler", currentProgram.getCompilerSpec().getCompilerSpecID().toString());
        metadata.addProperty("ghidra_version", ghidra.framework.Application.getApplicationVersion());
        metadata.addProperty("analysis", "Ghidra default auto-analysis; static observations only");
        TreeMap<String, Function> functions = new TreeMap<>();
        for (Function f : currentProgram.getFunctionManager().getFunctions(true)) functions.put(address(f), f);
        for (Function f : currentProgram.getFunctionManager().getExternalFunctions()) functions.put(address(f), f);
        StringBuilder enumeration = new StringBuilder();
        int external = 0;
        for (Function f : functions.values()) {
            monitor.checkCancelled();
            enumeration.append(gson.toJson(identity(f))).append('\n');
            if (f.isExternal()) external++;
        }
        save(output.resolve("functions.jsonl"), enumeration.toString());
        metadata.addProperty("function_count", functions.size());
        metadata.addProperty("external_count", external);
        StringBuilder symbols = new StringBuilder();
        SymbolIterator iterator = currentProgram.getSymbolTable().getAllSymbols(true);
        while (iterator.hasNext()) {
            Symbol symbol = iterator.next();
            if (!symbol.isExternal() && !symbol.isExternalEntryPoint()) continue;
            JsonObject row = object();
            row.addProperty("address", symbol.getAddress().toString());
            row.addProperty("name", symbol.getName(true));
            row.addProperty("external", symbol.isExternal());
            row.addProperty("entry_point", symbol.isExternalEntryPoint());
            symbols.append(gson.toJson(row)).append('\n');
        }
        save(output.resolve("interfaces.jsonl"), symbols.toString());
        StringBuilder types = new StringBuilder();
        Iterator<DataType> dataTypes = currentProgram.getDataTypeManager().getAllDataTypes();
        while (dataTypes.hasNext()) {
            DataType type = dataTypes.next();
            JsonObject row = object();
            row.addProperty("path", type.getPathName());
            row.addProperty("display", type.getDisplayName());
            row.addProperty("length", type.getLength());
            row.addProperty("kind", type.getClass().getSimpleName());
            types.append(gson.toJson(row)).append('\n');
        }
        save(output.resolve("types.jsonl"), types.toString());
        save(output.resolve("analysis.json"), gson.toJson(metadata) + "\n");
        if (limit == 0) {
            JsonObject result = object(); result.addProperty("run_id", args[4]); result.addProperty("attempted", 0);
            save(output.resolve("batch-result.json"), gson.toJson(result));
            println("RECOVERY inventory complete: " + functions.size()); return;
        }
        Map<String, String> previous = new HashMap<>();
        Path journal = output.resolve("decompilation.jsonl");
        if (Files.exists(journal)) {
            for (String line : Files.readAllLines(journal, StandardCharsets.UTF_8)) {
                if (line.isBlank()) continue;
                try {
                    JsonObject row = JsonParser.parseString(line).getAsJsonObject();
                    previous.put(row.get("address").getAsString(), row.get("status").getAsString());
                } catch (JsonParseException error) {
                    throw new IOException("Invalid journal record; preserve and repair it before resuming", error);
                }
            }
        }
        DecompInterface decompiler = new DecompInterface();
        if (!decompiler.openProgram(currentProgram)) throw new IOException("Decompiler could not open program");
        int attempted = 0;
        try (BufferedWriter writer = Files.newBufferedWriter(journal, StandardCharsets.UTF_8,
                StandardOpenOption.CREATE, StandardOpenOption.APPEND)) {
            for (Function f : functions.values()) {
                monitor.checkCancelled();
                if (f.isExternal()) continue;
                String entry = address(f);
                String old = previous.get(entry);
                Path code = output.resolve("pseudocode").resolve(entry.replace(':', '_') + ".c");
                if ("success".equals(old) && Files.isRegularFile(code)) continue;
                if (old != null && !"success".equals(old) && !retry &&
                        !(retryTimeouts && "timeout".equals(old))) continue;
                if (limit > 0 && attempted >= limit) break;
                JsonObject row = object();
                row.addProperty("address", entry);
                row.addProperty("name", f.getName(true));
                DecompileResults result = decompiler.decompileFunction(f, seconds, monitor);
                if (result.decompileCompleted() && result.getDecompiledFunction() != null) {
                    save(code, result.getDecompiledFunction().getC());
                    row.addProperty("status", "success");
                } else {
                    row.addProperty("status", result.isTimedOut() ? "timeout" : "failed");
                    row.addProperty("error", result.getErrorMessage());
                }
                writer.write(gson.toJson(row)); writer.newLine(); writer.flush();
                attempted++;
                if (attempted % 100 == 0) println("RECOVERY decompiled attempts: " + attempted);
            }
        } finally { decompiler.dispose(); }
        JsonObject result = object(); result.addProperty("run_id", args[4]); result.addProperty("attempted", attempted);
        save(output.resolve("batch-result.json"), gson.toJson(result));
        println("RECOVERY batch complete: " + attempted);
    }
}
