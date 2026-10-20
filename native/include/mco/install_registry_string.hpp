#pragma once
#include "mco/install_registry_runtime.hpp"
namespace mco {
// 1 profile read, 2 registry string query. The latter must write metadata[0]
// (type); metadata[1] starts at255. Buffer is a zeroed256-byte local.
struct RegistryStringCall {std::uint32_t id;std::span<const std::uint32_t> args;std::span<std::byte,256> buffer;std::span<std::uint32_t> metadata;};
using RegistryStringInvoke=std::uint32_t (*)(RegistryInstallState&,const RegistryStringCall&,void*);
struct RegistryStringPlatform {RegistryStringInvoke invoke{};void* user{};};
bool registry_read_string(RegistryInstallState&,const RegistryStringPlatform&,std::uint32_t name,std::span<std::byte> output,std::uint32_t count);
}
