#pragma once
#include "mco/install_registry_runtime.hpp"
namespace mco {
// Call ids: 1 close, 2 create, 3 profile text, 4 DWORD query, 5 integer scan.
// Buffers/metadata are live views; callbacks may mutate owner state.
struct RegistryQueryCall {
 std::uint32_t id;
 std::span<const std::uint32_t> args;
 std::span<std::byte> buffer;
 std::span<std::uint32_t> metadata;
 std::span<const std::byte> text;
};
using RegistryQueryInvoke=std::uint32_t (*)(RegistryInstallState&,const RegistryQueryCall&,void*);
struct RegistryQueryPlatform {RegistryQueryInvoke invoke{};void* user{};};
void registry_query_close(RegistryInstallState&,const RegistryQueryPlatform&);
bool registry_query_create(RegistryInstallState&,const RegistryQueryPlatform&,std::uint32_t root,std::uint32_t path,std::uint32_t access,std::uint32_t owner_identity);
bool registry_query_integer(RegistryInstallState&,const RegistryQueryPlatform&,std::uint32_t name,std::span<std::byte,4> output);
bool registry_read_integer(RegistryInstallState&,const RegistryQueryPlatform&,std::uint32_t name,std::span<std::byte,4> output);
}
