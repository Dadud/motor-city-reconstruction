#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x436280; Read a word from the current record.
std::uint32_t record_related_value(std::span<const std::byte> record);
}
