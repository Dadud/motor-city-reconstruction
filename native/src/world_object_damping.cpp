#include "mco/world_object_damping.hpp"
#include <cmath>

namespace mco {
WorldObjectMotion update_world_object_motion(WorldObjectMotion state) noexcept {
    if (state.contact_counter != 0) {
        for (auto& angle : state.angular_velocity) angle *= 0.9f;
        return state;
    }
    for (auto& velocity : state.linear_velocity)
        if (std::fabs(velocity) < 0.5f) velocity = 0.0f;
    if (std::fabs(state.angular_velocity[0]) < 0.05f) state.angular_velocity[1] = 0.0f;
    if (std::fabs(state.angular_velocity[1]) < 0.05f) state.angular_velocity[1] = 0.0f;
    if (std::fabs(state.angular_velocity[2]) < 0.05f) state.angular_velocity[1] = 0.0f;
    return state;
}
}
