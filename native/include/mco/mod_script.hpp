#pragma once

#include <cstddef>
#include <string>
#include <vector>

namespace mco {

// script-alpha-1 is an offline research registry, not a gameplay ABI.
struct ModResourceDefinition {
    std::string id;
    std::string kind;
    std::string label;
};

struct ModScriptPackage {
    std::string api_version;
    std::string id;
    std::string version;
    std::vector<ModResourceDefinition> resources;
    std::string source;
};

enum class ModResearchEvent { inspect, preview };
enum class ModExecutionMode { offline, online };

struct ModScriptResult {
    bool success;
    std::string error;
    std::vector<ModResourceDefinition> resources;
    std::vector<std::string> notes;
};

// Fresh bounded Lua state; registration init followed by one explicit event.
// Failure returns no partially registered content. No package file I/O occurs.
[[nodiscard]] ModScriptResult run_mod_script(
    const ModScriptPackage& package, ModResearchEvent event,
    ModExecutionMode mode, std::size_t instruction_budget = 100'000);

} // namespace mco
