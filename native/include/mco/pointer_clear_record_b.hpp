#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x429440; Clear an optional pointer target and record its original identity.
void pointer_clear_record_b(std::span<std::byte> target, std::uint32_t target_id, std::uint32_t &record);
}
