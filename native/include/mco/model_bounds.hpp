#pragma once
#include "mco/fce.hpp"
#include <optional>
namespace mco {
struct PartBounds { Vec3 minimum, maximum; };
// Original 0x4c3e50; caller establishes selection/scaling before this primitive.
std::optional<PartBounds> transformed_part_bounds(const FcePart& part, bool mirrored=false);
}
