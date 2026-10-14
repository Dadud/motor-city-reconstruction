#include "mco/script_runtime.hpp"

extern "C" {
#include <lua.h>
#include <lauxlib.h>
#include <lualib.h>
}

#include <cstdlib>
#include <initializer_list>

namespace mco {
namespace {

constexpr std::size_t memory_limit = 8 * 1024 * 1024;
constexpr std::size_t source_limit = 1024 * 1024;
constexpr std::size_t maximum_budget = 100'000'000;

struct Limits {
    std::size_t used = 0;
    std::size_t remaining;
};

void* allocate(void* userdata, void* pointer, std::size_t old_size,
               std::size_t new_size) {
    auto& limits = *static_cast<Limits*>(userdata);
    // For a new allocation Lua supplies an object type in old_size.
    if (pointer == nullptr) old_size = 0;
    if (new_size == 0) {
        limits.used -= old_size;
        std::free(pointer);
        return nullptr;
    }
    if (new_size > memory_limit - (limits.used - old_size)) return nullptr;
    void* result = std::realloc(pointer, new_size);
    if (result != nullptr) limits.used = limits.used - old_size + new_size;
    return result;
}

void count_instruction(lua_State* state, lua_Debug*) {
    void* userdata = nullptr;
    lua_getallocf(state, &userdata);
    auto& limits = *static_cast<Limits*>(userdata);
    if (limits.remaining == 0) luaL_error(state, "instruction budget exhausted");
    --limits.remaining;
}

void remove_global(lua_State* state, const char* name) {
    lua_pushnil(state);
    lua_setglobal(state, name);
}

int initialize(lua_State* state) {
    luaL_requiref(state, LUA_GNAME, luaopen_base, 1);
    lua_pop(state, 1);
    // Prevent dynamic loading, host output, collection controls, and catching a
    // budget exception in an endless protected-call loop. No coroutine library.
    for (const char* name : {"dofile", "loadfile", "load", "print", "warn",
                             "collectgarbage", "pcall", "xpcall",
                             "setmetatable", "getmetatable"}) {
        remove_global(state, name);
    }
    luaL_requiref(state, LUA_MATHLIBNAME, luaopen_math, 1);
    lua_pop(state, 1);
    luaL_requiref(state, LUA_STRLIBNAME, luaopen_string, 1);
    lua_pop(state, 1);
    // Binary serialization exposes VM bytecode rather than the script API.
    lua_getglobal(state, LUA_STRLIBNAME);
    // Pattern backtracking executes in C, outside the instruction budget.
    for (const char* name : {"dump", "find", "match", "gmatch", "gsub"}) {
        lua_pushnil(state);
        lua_setfield(state, -2, name);
    }
    lua_pop(state, 1);
    luaL_requiref(state, LUA_TABLIBNAME, luaopen_table, 1);
    lua_pop(state, 1);
    luaL_requiref(state, LUA_UTF8LIBNAME, luaopen_utf8, 1);
    lua_pop(state, 1);
    return 0;
}

ScriptResult failure(lua_State* state) {
    const char* message = lua_type(state, -1) == LUA_TSTRING
        ? lua_tostring(state, -1) : nullptr;
    return {false, message != nullptr ? message : "script failed"};
}

struct State {
    lua_State* value;
    ~State() { lua_close(value); }
};

} // namespace

ScriptResult run_script(std::string_view source, std::size_t instruction_budget) {
    if (instruction_budget == 0 || instruction_budget > maximum_budget)
        return {false, "instruction budget must be between 1 and 100000000"};
    if (source.size() > source_limit)
        return {false, "script source exceeds 1 MiB"};
    Limits limits{0, instruction_budget};
    lua_State* raw = lua_newstate(allocate, &limits);
    if (raw == nullptr) return {false, "cannot allocate script state"};
    State state{raw};
    lua_pushcfunction(raw, initialize);
    if (lua_pcall(raw, 0, 0, 0) != LUA_OK) return failure(raw);
    if (luaL_loadbufferx(raw, source.empty() ? "" : source.data(), source.size(),
                         "mod script", "t") != LUA_OK) return failure(raw);
    lua_sethook(raw, count_instruction, LUA_MASKCOUNT, 1);
    if (lua_pcall(raw, 0, 0, 0) != LUA_OK) return failure(raw);
    return {true, {}};
}

} // namespace mco
