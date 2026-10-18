#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x436c40; Copy the current record state in the original staged-word and MOVSD order.
void record_state_copy48(std::span<std::byte,48> destination, std::span<const std::byte> record);
}
