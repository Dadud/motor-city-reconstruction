#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x429460; Clear an optional pointer target and record its original identity.
void pointer_clear_record_c(std::span<std::byte> target, std::uint32_t target_id, std::uint32_t &record);
}
