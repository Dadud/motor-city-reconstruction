#pragma once
#include <array>
#include <cstddef>
#include <span>
namespace mco {
// Original 0x53a1f0..0x53ab90; builds the 0x4a8-byte startup record the
// caller copies to owner+0x17ec. model may be empty for the authored
// default-axle branch; area_query is the supplied FUN_00483450 return.
// Returns false on the original marker-search failure (record untouched).
bool startup_record(std::span<const std::byte> owner,
    std::span<const std::byte> configuration, bool has_model,
    std::span<const std::byte> model, float area_query,
    std::array<std::byte,0x4a8>& record);
}
