#pragma once
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
struct RegistryInstallState {std::span<std::byte,0x210> image;std::uint32_t language{};};
// Calls: 1 path preparation; 2 RegCloseKey; 3 RegOpenKeyExA;
// 4 strncpy; 5 language RegOpenKeyExA; 6 language RegQueryValueExA.
using RegistryInstallInvoke=std::uint32_t (*)(RegistryInstallState&,std::uint32_t,std::span<const std::uint32_t>,std::span<std::byte>,void*);
struct RegistryInstallPlatform {RegistryInstallInvoke invoke{};void* user{};};
void registry_install_construct(RegistryInstallState&,const RegistryInstallPlatform&,std::uint32_t root,std::uint32_t path,std::uint32_t access);
bool registry_install_reopen(RegistryInstallState&,const RegistryInstallPlatform&,std::uint32_t root,std::uint32_t path,std::uint32_t access);
bool registry_install_is_open(const RegistryInstallState&);
void registry_install_language(RegistryInstallState&,const RegistryInstallPlatform&);
}
