#include "mco/mod_script.hpp"

#include <iostream>
#include <string>

int main() {
    int failures = 0;
    const auto require = [&](bool condition, const char* message) {
        if (!condition) { std::cerr << message << '\n'; ++failures; }
    };
    mco::ModScriptPackage package{"script-alpha-1", "example.garage", "1.0.0",
        {{"example.garage:body", "vehicle", "Declared body"}}, R"(
            assert(mco.api_version == 'script-alpha-1')
            assert(io == nil and os == nil and package == nil and debug == nil)
            assert(load == nil and dofile == nil and pcall == nil and coroutine == nil)
            assert(string.dump == nil and setmetatable == nil and getmetatable == nil)
            assert(string.find == nil and string.match == nil and string.gmatch == nil and string.gsub == nil)
            mco.register_resource('ui', 'example.garage:title', 'Original garage')
            mco.on('inspect', function(event)
                assert(event.offline and event.name == 'inspect')
                assert(event.package_id == 'example.garage')
                mco.emit_note('First inspection note')
            end)
            mco.on('inspect', function(event) mco.emit_note('Second inspection note') end)
            mco.on('preview', function(event) mco.emit_note('Preview note') end)
        )"};
    const auto run = [&](const std::string& source, std::size_t budget = 100'000) {
        auto edited = package;
        edited.source = source;
        return mco::run_mod_script(edited, mco::ModResearchEvent::inspect, mco::ModExecutionMode::offline, budget);
    };
    const auto result = mco::run_mod_script(package, mco::ModResearchEvent::inspect, mco::ModExecutionMode::offline);
    require(result.success && result.resources.size() == 2 && result.notes.size() == 2,
            "declarative and scripted registration plus research event should work");
    if (result.success && result.resources.size() == 2 && result.notes.size() == 2) {
        require(result.resources[0].id == "example.garage:body" && result.resources[1].id == "example.garage:title",
                "resources should use deterministic ID ordering");
        require(result.notes[0] == "First inspection note" && result.notes[1] == "Second inspection note",
                "handlers must execute in registration order");
    }
    const auto preview = mco::run_mod_script(package, mco::ModResearchEvent::preview, mco::ModExecutionMode::offline);
    require(preview.success && preview.notes.size() == 1 && preview.notes[0] == "Preview note", "only selected event should execute");
    require(!mco::run_mod_script(package, mco::ModResearchEvent::inspect, mco::ModExecutionMode::online).success,
            "online must be refused before executing script");
    auto wrong = package;
    wrong.api_version = "data-alpha-1";
    require(!mco::run_mod_script(wrong, mco::ModResearchEvent::inspect, mco::ModExecutionMode::offline).success,
            "data API must not silently become script API");
    wrong = package; wrong.id = "../escape";
    require(!mco::run_mod_script(wrong, mco::ModResearchEvent::inspect, mco::ModExecutionMode::offline).success, "invalid package ID must fail");
    wrong = package; wrong.version = "01.0.0";
    require(!mco::run_mod_script(wrong, mco::ModResearchEvent::inspect, mco::ModExecutionMode::offline).success, "noncanonical version must fail");
    require(!run("mco.register_resource('vehicle', 'example.garage:body', 'Duplicate')").success, "duplicate declaration must fail");
    require(!run("mco.register_resource('vehicle', 'other.mod:body', 'Foreign')").success, "foreign namespace must fail");
    require(!run("mco.register_resource('engine', 'example.garage:engine', 'Invented')").success, "unsupported kind must fail");
    require(!run("mco.on('race', function() end)").success, "gameplay event must fail");
    require(!run("mco.emit_note('init note')").success, "init cannot emit event notes");
    require(!run("mco.on('inspect', function() mco.register_resource('ui', 'example.garage:late', 'Late') end)").success,
            "event cannot register content");
    require(!run("mco.on('inspect', function() mco.on('inspect', function() end) end)").success,
            "event cannot register handlers");
    require(!run("for i=1,257 do mco.register_resource('ui', 'example.garage:id' .. i, 'Title') end").success, "resource bound must fail");
    require(!run("for i=1,17 do mco.on('inspect', function() end) end").success, "handler bound must fail");
    require(!run("mco.on('inspect', function() for i=1,65 do mco.emit_note('note') end end)").success, "note bound must fail");
    const auto loop = run("mco.on('inspect', function() while true do end end)", 100);
    require(!loop.success && loop.error.find("instruction budget") != std::string::npos && loop.resources.empty(),
            "event loop must exhaust budget and discard partial registrations");
    const auto memory = run("local huge = string.rep('x', 16 * 1024 * 1024)");
    require(!memory.success && memory.error.find("memory") != std::string::npos, "memory limit must fail safely");
    require(!run(std::string("\x1bLua", 4)).success, "bytecode must fail");
    require(!run("error(42)").success && !run("error({})").success,
            "non-string error objects must fail without host coercion");
    require(!run("setmetatable({}, {__gc=function() while true do end end})", 100).success,
            "finalizers must be rejected before unbounded state teardown");
    require(!run("string.find(string.rep('a',1000), string.rep('a*',30)..'b')", 1000).success,
            "pattern backtracking must be unavailable outside the VM budget");
    require(!run("", 0).success, "zero budget must fail");
    require(!run(std::string(1024 * 1024 + 1, ' ')).success, "source bound must fail");
    require(run("").success, "fresh execution should recover after failures");
    return failures == 0 ? 0 : 1;
}
