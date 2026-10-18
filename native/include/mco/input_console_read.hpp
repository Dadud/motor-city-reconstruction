#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/input_console_state.hpp"
namespace mco {
// Original 0x7b0cd6, 0x7b0e17, 0x7b0d0e, 0x7b0e33, 0x7b0f33, 0x7b1fe9; Read or probe console events with original locking, pending-byte, mode restoration and overlapping scan decoding.
std::uint32_t input_console_read(InputConsoleState &state, const InputConsolePlatform &platform);
}
