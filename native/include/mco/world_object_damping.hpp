#pragma once
#include <array>
#include <cstdint>

namespace mco {
struct WorldObjectMotion {
    std::int16_t contact_counter{};
    std::array<float, 3> linear_velocity{};
    std::array<float, 3> angular_velocity{};
};

// Translation of the observed mutation behavior at 0x5779d0.
WorldObjectMotion update_world_object_motion(WorldObjectMotion state) noexcept;
}
