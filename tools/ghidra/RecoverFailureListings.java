// Preserve exact instruction listings for failed decompilations, privately.
//@category MotorCity.Recovery
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import com.google.gson.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class RecoverFailureListings extends GhidraScript {
    @Override public void run() throws Exception {
        String[] args = getScriptArgs();
        Path output = Paths.get(args[0]);
        Map<String, String> statuses = new TreeMap<>();
        Path journal = output.resolve("decompilation.jsonl");
        if (Files.exists(journal)) {
            for (String line : Files.readAllLines(journal, StandardCharsets.UTF_8)) {
                if (line.isBlank()) continue;
                JsonObject row = JsonParser.parseString(line).getAsJsonObject();
                statuses.put(row.get("address").getAsString(), row.get("status").getAsString());
            }
        }
        Files.createDirectories(output.resolve("failed-listings"));
        int count = 0;
        for (Map.Entry<String, String> record : statuses.entrySet()) {
            if ("success".equals(record.getValue())) continue;
            Function function = currentProgram.getFunctionManager().getFunctionAt(toAddr(record.getKey()));
            if (function == null) throw new IllegalStateException("Failed function entry is no longer defined");
            StringBuilder text = new StringBuilder();
            text.append("; static Ghidra listing: ").append(function.getName(true)).append('\n');
            text.append("; ").append(function.getSignature()).append('\n');
            for (Instruction instruction : currentProgram.getListing().getInstructions(function.getBody(), true)) {
                monitor.checkCancelled();
                text.append(instruction.getAddress()).append("  ").append(instruction).append('\n');
            }
            Files.writeString(output.resolve("failed-listings").resolve(record.getKey().replace(':', '_')+".asm"),
                text.toString(), StandardCharsets.UTF_8);
            count++;
        }
        JsonObject result = new JsonObject();
        result.addProperty("run_id", args[1]); result.addProperty("attempted", count);
        Files.writeString(output.resolve("batch-result.json"), result.toString(), StandardCharsets.UTF_8);
        println("RECOVERY failed instruction listings: " + count);
    }
}
