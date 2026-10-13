#pragma once

#include <cstddef>
#include <string>
#include <string_view>

namespace mco {

struct ScriptResult {
    bool success;
    std::string error;
};

// Each call owns a fresh state capped at 8 MiB. Only text chunks are accepted.
// The budget counts Lua VM instructions, not wall time spent in library calls.
[[nodiscard]] ScriptResult run_script(std::string_view source,
                                      std::size_t instruction_budget);

} // namespace mco
