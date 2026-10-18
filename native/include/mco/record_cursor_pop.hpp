#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x435f80; Retreat the current record cursor by 256 bytes with an unsigned clamp.
std::uint32_t record_cursor_pop(std::uint32_t cursor, std::uint32_t base);
}
