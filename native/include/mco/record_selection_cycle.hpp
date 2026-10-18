#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/record_machine.hpp"
namespace mco {
// Original 0x436520; Cycle camera presets or mode-table selections for a viewport.
void record_selection_cycle(RecordMachine &machine, std::span<const std::byte> pairs, std::span<const std::byte, 36> modes, std::span<const std::byte, 12> context, std::uint32_t mode, std::uint32_t &counter0, std::uint32_t &counter1, std::span<const std::byte> subjects, std::uint32_t viewport);
}
