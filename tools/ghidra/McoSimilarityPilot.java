// Seed a private BSim database from a bounded sample of an existing analysis.
// Analysis-generated names are triage candidates, never library equivalence proofs.
//@category MCO
import java.io.*;
import java.nio.file.*;
import java.util.*;
import com.google.gson.*;
import ghidra.app.script.GhidraScript;
import ghidra.features.bsim.query.*;
import ghidra.features.bsim.query.description.*;
import ghidra.features.bsim.query.file.BSimH2FileDBConnectionManager;
import ghidra.features.bsim.query.protocol.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.SourceType;
import ghidra.feature.fid.service.*;

public class McoSimilarityPilot extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 3) throw new IllegalArgumentException("output-directory target-sha256 limit");
        if (!args[1].equals(currentProgram.getExecutableSHA256()))
            throw new IOException("retained program target mismatch");
        Path output = Path.of(args[0]);
        int limit = Integer.parseInt(args[2]);
        if (limit < 1 || limit > 200) throw new IllegalArgumentException("limit must be 1..200");
        FidService fid = new FidService();
        Map<Function, List<FidMatch>> fidHits = new LinkedHashMap<>();
        try (var query = fid.openFidQueryService(currentProgram.getLanguage(), false)) {
            for (FidSearchResult result : fid.processProgram(currentProgram, query,
                    fid.getDefaultScoreThreshold(), monitor)) {
                if (result.matches != null && !result.matches.isEmpty())
                    fidHits.put(result.function, result.matches);
            }
            // Materialize candidate strings while the read-only FID query is open.
            Map<Function, List<Map<String, Object>>> matches = new HashMap<>();
            for (var entry : fidHits.entrySet()) {
                List<Map<String, Object>> rows = new ArrayList<>();
                for (FidMatch match : entry.getValue()) {
                    if (rows.size() == 3) break;
                    rows.add(Map.of("name", match.getFunctionRecord().getName(),
                        "library", match.getLibraryRecord().toString(),
                        "score", match.getOverallScore()));
                }
                matches.put(entry.getKey(), rows);
            }
            runPilot(output, limit, matches, fid.getDefaultScoreThreshold());
        }
    }

    private void runPilot(Path output, int limit,
            Map<Function, List<Map<String, Object>>> fidHits, float fidThreshold) throws Exception {
        List<Function> named = new ArrayList<>(), unnamed = new ArrayList<>();
        Map<String, Integer> sources = new TreeMap<>();
        int total = 0;
        for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
            monitor.checkCancelled();
            total++;
            String source = f.getSymbol().getSource().toString();
            sources.merge(source, 1, Integer::sum);
            if (f.isExternal() || f.isThunk() || f.getBody().getNumAddresses() < 32) continue;
            if (f.getSymbol().getSource() == SourceType.ANALYSIS && !f.getName().startsWith("FUN_"))
                named.add(f);
            else unnamed.add(f);
        }
        List<Function> selected = new ArrayList<>();
        List<Function> fidFunctions = new ArrayList<>(fidHits.keySet());
        fidFunctions.sort(Comparator.comparing(Function::getEntryPoint));
        for (List<Function> group : List.of(fidFunctions, named, unnamed)) {
            for (Function f : group) {
                if (selected.size() == limit) break;
                if (!f.isExternal() && !f.isThunk() && !selected.contains(f)) selected.add(f);
            }
        }
        if (selected.isEmpty()) throw new IOException("no eligible functions");
        List<Map<String, Object>> candidates = new ArrayList<>();
        for (Function f : selected) {
            candidates.add(Map.of("address", "0x" + f.getEntryPoint().toString(),
                "name", f.getName(), "source", f.getSymbol().getSource().toString(),
                "body_bytes", f.getBody().getNumAddresses(),
                "disposition", "unreviewed_candidate",
                "fid_candidates", fidHits.getOrDefault(f, List.of())));
        }
        // Read the retained database; do not change names, types or dispositions.
        BSimServerInfo server = new BSimServerInfo(output.resolve("mco-pilot").toString());
        if (Files.exists(output.resolve("mco-pilot" + BSimServerInfo.H2_FILE_EXTENSION)))
            throw new IOException("refusing to replace existing BSim database");
        int descriptions;
        int signatures = 0;
        try (FunctionDatabase db = BSimClientFactory.buildClient(server, false)) {
            CreateDatabase create = new CreateDatabase();
            create.info = new DatabaseInformation();
            create.info.databasename = "mco-pilot";
            create.info.trackcallgraph = true;
            create.config_template = "medium_nosize";
            if (create.execute(db) == null) throw new IOException(db.getLastError().message);
            if (!db.initialize()) throw new IOException(db.getLastError().message);
            DatabaseInformation info = db.getInfo();
            GenSignatures generator = new GenSignatures(info.trackcallgraph);
            try {
                generator.setVectorFactory(db.getLSHVectorFactory());
                generator.addExecutableCategories(info.execats);
                generator.addFunctionTags(info.functionTags);
                generator.addDateColumnName(info.dateColumnName);
                generator.openProgram(currentProgram, null, null, null,
                    "ghidra://localhost/" + state.getProject().getName(),
                    GenSignatures.getPathFromDomainFile(currentProgram));
                generator.scanFunctions(selected.iterator(), selected.size(), monitor);
                DescriptionManager manager = generator.getDescriptionManager();
                descriptions = manager.numFunctions();
                var records = manager.listAllFunctions();
                while (records.hasNext()) {
                    if (records.next().getSignatureRecord() != null) signatures++;
                }
                if (signatures == 0) throw new IOException("no BSim signatures generated");
                manager.listAllFunctions().forEachRemaining(f -> f.sortCallgraph());
                InsertRequest insert = new InsertRequest();
                insert.manage = manager;
                if (insert.execute(db) == null) throw new IOException(db.getLastError().message);
                QueryExeCount count = new QueryExeCount();
                ResponseExe response = count.execute(db);
                if (response == null || response.recordCount != 1)
                    throw new IOException("BSim executable-count verification failed");
            } finally { generator.dispose(); }
        } finally {
            var source = BSimH2FileDBConnectionManager.getDataSourceIfExists(server);
            if (source != null) source.dispose();
        }
        Map<String, Object> report = new LinkedHashMap<>();
        report.put("target_sha256", currentProgram.getExecutableSHA256());
        report.put("ghidra_version", ghidra.framework.Application.getApplicationVersion());
        report.put("authority", "supplemental retained-Ghidra analysis; not REA Evidence");
        report.put("function_count", total);
        report.put("symbol_source_counts", sources);
        report.put("analysis_named_candidates", named.size());
        report.put("fid_matched_functions_unreviewed", fidHits.size());
        report.put("fid_score_threshold", fidThreshold);
        report.put("selected_functions", selected.size());
        report.put("signature_records", signatures);
        report.put("description_records_including_callees", descriptions);
        report.put("reference_executables", 1);
        report.put("candidates", candidates);
        report.put("limitations", List.of("Seed database only; no cross-binary matches reviewed",
            "Analysis names are not proof of Function ID attribution or library equivalence",
            "No automatic disposition/type/name changes; static analysis only"));
        Files.writeString(output.resolve("report.json"),
            new GsonBuilder().setPrettyPrinting().create().toJson(report) + "\n");
        println("MCO_SIMILARITY_PILOT_OK functions=" + selected.size() + " signatures=" + signatures);
    }
}
