#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x437ae0; Update one word of the current record, preserving neighboring state.
void record_flag_toggle(std::span<std::byte> record);
}
