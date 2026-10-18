#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/record_machine.hpp"
namespace mco {
// Original 0x432620; Push or replace a record with matched-pair snapshot and callback semantics.
void record_transition(RecordMachine &machine, std::span<const std::byte> pairs, std::uint32_t identifier, std::uint32_t handler, std::uint32_t push, std::uint32_t parameter);
}
