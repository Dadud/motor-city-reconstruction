#include "mco/mod_script.hpp"

extern "C" {
#include <lua.h>
#include <lauxlib.h>
#include <lualib.h>
}

#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <initializer_list>
#include <string_view>

namespace mco {
namespace {
constexpr std::size_t memory_limit = 8 * 1024 * 1024;
constexpr std::size_t source_limit = 1024 * 1024;
constexpr std::size_t resource_limit = 256;
constexpr std::size_t note_limit = 64;
constexpr std::size_t handler_limit = 16;

struct Limits { std::size_t used = 0; std::size_t remaining; };
void* allocate(void* userdata, void* pointer, std::size_t old_size, std::size_t new_size) {
    auto& limits = *static_cast<Limits*>(userdata);
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

bool identifier(std::string_view value) {
    if (value.empty() || value.size() > 80 || value[0] < 'a' || value[0] > 'z') return false;
    bool separator = false;
    for (char c : value) {
        if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9')) separator = false;
        else if ((c == '.' || c == '_' || c == '-') && !separator) separator = true;
        else return false;
    }
    return !separator;
}
bool version(std::string_view value) {
    if (value.empty() || value.size() > 64) return false;
    unsigned components = 0;
    std::size_t start = 0;
    for (std::size_t end = 0; end <= value.size(); ++end) {
        if (end != value.size() && value[end] != '.') {
            if (value[end] < '0' || value[end] > '9') return false;
            continue;
        }
        if (end == start || (end - start > 1 && value[start] == '0')) return false;
        ++components;
        start = end + 1;
    }
    return components == 3;
}
bool kind(std::string_view value) {
    return value == "vehicle" || value == "component" || value == "track" ||
           value == "material" || value == "sound" || value == "ui";
}
bool owned_id(std::string_view value, std::string_view owner) {
    return value.size() > owner.size() + 1 && value.substr(0, owner.size()) == owner &&
           value[owner.size()] == ':' && identifier(value.substr(owner.size() + 1));
}
bool bounded_text(std::string_view value) {
    // Byte strings are intentionally limited to printable ASCII in this API.
    if (value.empty() || value.size() > 1024) return false;
    for (unsigned char c : value) if (c < 32 || c > 126) return false;
    return true;
}

// Callbacks hold no C++ owning objects across Lua errors/longjmp.
const char* string_argument(lua_State* state, int index, std::size_t* length) {
    if (lua_type(state, index) != LUA_TSTRING) luaL_error(state, "argument must be a string");
    return lua_tolstring(state, index, length);
}
int register_resource(lua_State* state) {
    if (lua_gettop(state) != 3) return luaL_error(state, "register_resource expects kind, id, label");
    lua_getfield(state, lua_upvalueindex(1), "phase");
    const bool initial = std::strcmp(lua_tostring(state, -1), "init") == 0;
    lua_pop(state, 1);
    if (!initial) return luaL_error(state, "resource registration is allowed only during init");
    std::size_t kind_size, id_size, label_size, owner_size;
    const char* k = string_argument(state, 1, &kind_size);
    const char* id = string_argument(state, 2, &id_size);
    const char* label = string_argument(state, 3, &label_size);
    lua_getfield(state, lua_upvalueindex(1), "package_id");
    const char* owner = lua_tolstring(state, -1, &owner_size);
    if (!kind({k, kind_size})) return luaL_error(state, "unsupported resource kind");
    if (!owned_id({id, id_size}, {owner, owner_size})) return luaL_error(state, "resource ID must use the package namespace");
    if (!bounded_text({label, label_size})) return luaL_error(state, "label must contain 1..1024 printable ASCII bytes");
    lua_pop(state, 1);
    lua_getfield(state, lua_upvalueindex(1), "resources");
    lua_getfield(state, -1, id);
    if (!lua_isnil(state, -1)) return luaL_error(state, "duplicate resource ID");
    lua_pop(state, 1);
    lua_getfield(state, lua_upvalueindex(1), "count");
    const auto count = lua_tointeger(state, -1);
    lua_pop(state, 1);
    if (count >= static_cast<lua_Integer>(resource_limit)) return luaL_error(state, "resource limit exceeded");
    lua_createtable(state, 0, 2);
    lua_pushvalue(state, 1); lua_setfield(state, -2, "kind");
    lua_pushvalue(state, 3); lua_setfield(state, -2, "label");
    lua_setfield(state, -2, id);
    lua_pushinteger(state, count + 1); lua_setfield(state, lua_upvalueindex(1), "count");
    return 0;
}
int on_event(lua_State* state) {
    if (lua_gettop(state) != 2) return luaL_error(state, "on expects event name and function");
    std::size_t length;
    const char* event = string_argument(state, 1, &length);
    if (!(std::string_view(event, length) == "inspect" || std::string_view(event, length) == "preview"))
        return luaL_error(state, "supported events are inspect and preview");
    luaL_checktype(state, 2, LUA_TFUNCTION);
    lua_getfield(state, lua_upvalueindex(1), "phase");
    if (std::strcmp(lua_tostring(state, -1), "init") != 0) return luaL_error(state, "event handlers may be registered only during init");
    lua_pop(state, 1);
    lua_getfield(state, lua_upvalueindex(1), event);
    const auto size = lua_rawlen(state, -1);
    if (size >= handler_limit) return luaL_error(state, "event handler limit exceeded");
    lua_pushvalue(state, 2); lua_rawseti(state, -2, static_cast<lua_Integer>(size + 1));
    return 0;
}
int emit_note(lua_State* state) {
    if (lua_gettop(state) != 1) return luaL_error(state, "emit_note expects one string");
    std::size_t length;
    const char* note = string_argument(state, 1, &length);
    if (!bounded_text({note, length})) return luaL_error(state, "note must contain 1..1024 printable ASCII bytes");
    lua_getfield(state, lua_upvalueindex(1), "phase");
    if (std::strcmp(lua_tostring(state, -1), "init") == 0) return luaL_error(state, "notes may be emitted only during an event");
    lua_pop(state, 1);
    lua_getfield(state, lua_upvalueindex(1), "notes");
    const auto size = lua_rawlen(state, -1);
    if (size >= note_limit) return luaL_error(state, "note limit exceeded");
    lua_pushvalue(state, 1); lua_rawseti(state, -2, static_cast<lua_Integer>(size + 1));
    return 0;
}
int initialize(lua_State* state) {
    // Host inputs are arguments to this protected initialization call.
    luaL_requiref(state, LUA_GNAME, luaopen_base, 1); lua_pop(state, 1);
    for (const char* name : {"dofile", "loadfile", "load", "print", "warn", "collectgarbage", "pcall", "xpcall"}) {
        lua_pushnil(state); lua_setglobal(state, name);
    }
    luaL_requiref(state, LUA_MATHLIBNAME, luaopen_math, 1); lua_pop(state, 1);
    luaL_requiref(state, LUA_STRLIBNAME, luaopen_string, 1); lua_pop(state, 1);
    lua_getglobal(state, "string"); lua_pushnil(state); lua_setfield(state, -2, "dump"); lua_pop(state, 1);
    luaL_requiref(state, LUA_TABLIBNAME, luaopen_table, 1); lua_pop(state, 1);
    luaL_requiref(state, LUA_UTF8LIBNAME, luaopen_utf8, 1); lua_pop(state, 1);
    lua_createtable(state, 0, 7);
    const int context = lua_gettop(state);
    lua_pushvalue(state, 1); lua_setfield(state, context, "package_id");
    lua_pushliteral(state, "init"); lua_setfield(state, context, "phase");
    lua_pushinteger(state, 0); lua_setfield(state, context, "count");
    for (const char* field : {"resources", "notes", "inspect", "preview"}) {
        lua_newtable(state); lua_setfield(state, context, field);
    }
    lua_pushvalue(state, context); lua_setfield(state, LUA_REGISTRYINDEX, "mco.mod_context");
    lua_createtable(state, 0, 4);
    lua_pushliteral(state, "script-alpha-1"); lua_setfield(state, -2, "api_version");
    lua_pushvalue(state, context); lua_pushcclosure(state, register_resource, 1); lua_setfield(state, -2, "register_resource");
    lua_pushvalue(state, context); lua_pushcclosure(state, on_event, 1); lua_setfield(state, -2, "on");
    lua_pushvalue(state, context); lua_pushcclosure(state, emit_note, 1); lua_setfield(state, -2, "emit_note");
    lua_setglobal(state, "mco");
    return 0;
}
int seed_resources(lua_State* state) {
    auto* package = static_cast<const ModScriptPackage*>(lua_touserdata(state, 1));
    lua_getfield(state, LUA_REGISTRYINDEX, "mco.mod_context");
    lua_pushcclosure(state, register_resource, 1);
    // Plain indices/pointers avoid debug STL iterator destructors across longjmp.
    for (std::size_t i = 0; i < package->resources.size(); ++i) {
        const ModResourceDefinition* resource = &package->resources[i];
        lua_pushvalue(state, -1);
        lua_pushlstring(state, resource->kind.data(), resource->kind.size());
        lua_pushlstring(state, resource->id.data(), resource->id.size());
        lua_pushlstring(state, resource->label.data(), resource->label.size());
        lua_call(state, 3, 0);
    }
    return 0;
}
int dispatch(lua_State* state) {
    const char* event = lua_tostring(state, 1);
    lua_getfield(state, LUA_REGISTRYINDEX, "mco.mod_context");
    lua_pushvalue(state, 1); lua_setfield(state, -2, "phase");
    lua_getfield(state, -1, event);
    const auto count = lua_rawlen(state, -1);
    for (std::size_t i = 1; i <= count; ++i) {
        lua_rawgeti(state, -1, static_cast<lua_Integer>(i));
        lua_createtable(state, 0, 3);
        lua_pushvalue(state, 1); lua_setfield(state, -2, "name");
        lua_pushboolean(state, 1); lua_setfield(state, -2, "offline");
        lua_getfield(state, -4, "package_id"); lua_setfield(state, -2, "package_id");
        lua_call(state, 1, 0);
    }
    return 0;
}
ModScriptResult failure(lua_State* state) {
    // Do not coerce numeric error objects: conversion can allocate after OOM.
    const char* error = lua_type(state, -1) == LUA_TSTRING ? lua_tostring(state, -1) : nullptr;
    return {false, error != nullptr ? error : "script failed", {}, {}};
}
struct State { lua_State* value; ~State() { lua_close(value); } };
}

ModScriptResult run_mod_script(const ModScriptPackage& package, ModResearchEvent event,
                               ModExecutionMode mode, std::size_t instruction_budget) {
    if (mode != ModExecutionMode::offline) return {false, "script-alpha-1 requires offline mode", {}, {}};
    if (package.api_version != "script-alpha-1") return {false, "unsupported script API version", {}, {}};
    if (!identifier(package.id) || !version(package.version)) return {false, "invalid package ID or exact version", {}, {}};
    if (event != ModResearchEvent::inspect && event != ModResearchEvent::preview) return {false, "unsupported research event", {}, {}};
    if (instruction_budget == 0 || instruction_budget > 100'000'000) return {false, "invalid instruction budget", {}, {}};
    if (package.source.size() > source_limit || package.resources.size() > resource_limit) return {false, "package source/resource limit exceeded", {}, {}};
    for (const auto& resource : package.resources) {
        if (!owned_id(resource.id, package.id) || !kind(resource.kind) || !bounded_text(resource.label))
            return {false, "invalid declarative resource ID, kind or label", {}, {}};
    }
    Limits limits{0, instruction_budget};
    lua_State* raw = lua_newstate(allocate, &limits);
    if (raw == nullptr) return {false, "cannot allocate script state", {}, {}};
    State state{raw};
    lua_pushcfunction(raw, initialize); lua_pushlstring(raw, package.id.data(), package.id.size());
    if (lua_pcall(raw, 1, 0, 0) != LUA_OK) return failure(raw);
    lua_pushcfunction(raw, seed_resources); lua_pushlightuserdata(raw, const_cast<ModScriptPackage*>(&package));
    if (lua_pcall(raw, 1, 0, 0) != LUA_OK) return failure(raw);
    if (luaL_loadbufferx(raw, package.source.data(), package.source.size(), "mod research script", "t") != LUA_OK) return failure(raw);
    lua_sethook(raw, count_instruction, LUA_MASKCOUNT, 1);
    if (lua_pcall(raw, 0, 0, 0) != LUA_OK) return failure(raw);
    lua_pushcfunction(raw, dispatch); lua_pushstring(raw, event == ModResearchEvent::inspect ? "inspect" : "preview");
    if (lua_pcall(raw, 1, 0, 0) != LUA_OK) return failure(raw);
    ModScriptResult result{true, {}, {}, {}};
    lua_getfield(raw, LUA_REGISTRYINDEX, "mco.mod_context");
    lua_getfield(raw, -1, "resources");
    lua_pushnil(raw);
    while (lua_next(raw, -2) != 0) {
        ModResourceDefinition item;
        item.id = lua_tostring(raw, -2);
        lua_getfield(raw, -1, "kind"); item.kind = lua_tostring(raw, -1); lua_pop(raw, 1);
        lua_getfield(raw, -1, "label"); item.label = lua_tostring(raw, -1); lua_pop(raw, 1);
        result.resources.push_back(std::move(item));
        lua_pop(raw, 1);
    }
    lua_pop(raw, 1);
    lua_getfield(raw, -1, "notes");
    const auto notes = lua_rawlen(raw, -1);
    for (std::size_t i = 1; i <= notes; ++i) {
        lua_rawgeti(raw, -1, static_cast<lua_Integer>(i));
        result.notes.emplace_back(lua_tostring(raw, -1)); lua_pop(raw, 1);
    }
    std::sort(result.resources.begin(), result.resources.end(), [](const auto& a, const auto& b) { return a.id < b.id; });
    return result;
}
} // namespace mco
