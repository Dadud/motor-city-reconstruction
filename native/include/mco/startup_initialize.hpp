#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/startup_state.hpp"
namespace mco {
// Original 0x6bfa10, 0x584c80; Preserve full startup branching, diagnostics and input setup order with explicit unresolved subsystem bridges.
void startup_initialize(StartupState &state, const StartupPlatform &platform);
}
