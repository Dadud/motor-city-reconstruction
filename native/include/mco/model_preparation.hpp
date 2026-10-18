#pragma once
#include "mco/fce.hpp"
#include <optional>
#include <span>
namespace mco {
// Original 0x4c4050/0x4c42d0; complete FCE byte images retain all three streams.
std::optional<Vec3> model_part_half_extents(std::span<const std::uint8_t> image,int part);
void model_scale_part_streams(std::span<std::uint8_t> image,int part,const Vec3& scales);
// Original 0x52bc60 after first type0x11 node selection. Empty images/absent
// part represent its missing-pointer gates. False means no alignment occurred.
bool model_align_secondary(std::span<std::uint8_t> secondary,
                           std::span<const std::uint8_t> reference,
                           std::optional<int> reference_part);
}
