#pragma once
#include <cstdint>
#include <span>
namespace mco {
// Original 0xb2bbe8..0xb2bce8. Identities are words, never host pointers.
struct CleanupRegistry { std::span<std::uint32_t,64> slots; };
using CleanupInvoke=void (*)(CleanupRegistry&,std::uint32_t identity,void* user);
struct CleanupRegistryPlatform {CleanupInvoke invoke{};void* user{};};
void cleanup_registry_register(CleanupRegistry&,std::uint32_t identity);
}
