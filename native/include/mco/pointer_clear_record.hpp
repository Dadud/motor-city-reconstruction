#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x429420; Clear a pointer target and record its identity.
void pointer_clear_record(std::span<std::byte> target, std::uint32_t target_id, std::uint32_t &record);
}
