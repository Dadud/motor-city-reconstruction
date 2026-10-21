#include "mco/world_object_maintenance.hpp"
#include <cmath>
#include <stdexcept>

namespace mco {
WorldObjectMaintenance maintain_world_object(
    WorldObjectMaintenance state,
    const std::function<WorldObjectMotion(WorldObjectMotion)>& update_motion) {
    if (!update_motion) throw std::invalid_argument("the 0x520c20 child callback is required");
    if (!state.active) return state;

    state.motion = update_motion(state.motion);
    auto& linear = state.motion.linear_velocity;
    auto& angular = state.motion.angular_velocity;
    const auto magnitude = std::sqrt(angular[0]*angular[0] +
                                     angular[1]*angular[1] + angular[2]*angular[2]);
    if (state.maintenance_value < state.reference_value) {
        for (auto& value : linear) value *= 0.99f;
        for (auto& value : angular) value *= 0.99f;
    }

    if (magnitude > 10.0f) {
        const auto factor = 10.0f / magnitude;
        for (auto& value : angular) value *= factor;
    }
    if (static_cast<std::uint16_t>(state.motion.contact_counter) > 32 &&
        state.maintenance_value == 0.0f && magnitude == 0.0f)
        angular[0] += 0.01f;
    return state;
}

std::vector<WorldObjectMaintenance> maintain_world_objects(
    const std::vector<WorldObjectMaintenance>& objects,
    const std::function<WorldObjectMotion(WorldObjectMotion)>& update_motion) {
    std::vector<WorldObjectMaintenance> result;
    result.reserve(objects.size());
    for (const auto& object : objects)
        result.push_back(maintain_world_object(object, update_motion));
    return result;
}
}
