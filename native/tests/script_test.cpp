#include "mco/script_runtime.hpp"

#include <iostream>
#include <string>

int main() {
    int failures = 0;
    const auto require = [&](bool condition, const char* message) {
        if (!condition) { std::cerr << message << '\n'; ++failures; }
    };
    require(mco::run_script("assert(math.sqrt(81) == 9); "
                            "assert(string.upper('mod') == 'MOD'); "
                            "assert(table.concat({'a','b'}) == 'ab'); "
                            "assert(utf8.len('hello') == 5)", 1000).success,
            "safe libraries should work");
    const auto loop = mco::run_script("while true do end", 100);
    require(!loop.success && loop.error.find("instruction budget") != std::string::npos,
            "infinite loop must exhaust budget");
    require(mco::run_script("assert(io == nil and os == nil and package == nil "
                            "and debug == nil and dofile == nil and loadfile == nil "
                            "and load == nil and pcall == nil and xpcall == nil "
                            "and coroutine == nil and string.dump == nil)", 1000).success,
            "host access and exception catching must be unavailable");
    require(!mco::run_script("io.open('secret', 'r')", 100).success,
            "file access must fail");
    const auto memory = mco::run_script("local s = string.rep('x', 16 * 1024 * 1024)", 1000);
    require(!memory.success && memory.error.find("memory") != std::string::npos,
            "oversized allocation must fail without crashing");
    require(!mco::run_script("", 0).success, "zero budget must fail");
    require(!mco::run_script("", 100'000'001).success, "excessive budget must fail");
    require(!mco::run_script("function (", 100).success, "invalid syntax must fail");
    require(!mco::run_script(std::string("\x1bLua", 4), 100).success,
            "binary chunks must be rejected");
    require(mco::run_script("assert(io == nil)", 100).success,
            "state must remain usable after a failed call");
    return failures == 0 ? 0 : 1;
}
