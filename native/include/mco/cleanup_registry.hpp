#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/cleanup_registry_state.hpp"
namespace mco {
// Original 0x6bf450, 0x6bf410; Register unique cleanup identities and invoke mutable slots in reverse order.
void cleanup_registry_run(CleanupRegistry &state, const CleanupRegistryPlatform &platform);
}
