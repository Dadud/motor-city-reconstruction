#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x436270; Read a word from the current record.
std::uint32_t record_identifier(std::span<const std::byte> record);
}
