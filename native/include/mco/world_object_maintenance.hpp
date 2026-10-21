#pragma once
#include "mco/world_object_damping.hpp"
#include <cstdint>
#include <functional>
#include <vector>

namespace mco {
struct WorldObjectMaintenance {
    WorldObjectMotion motion{};
    bool active{};
    float maintenance_value{}; // owner +0x350 (pfVar3[0xcf])
    float reference_value{};   // owner +0xd8 (pfVar3[0x31])
};

WorldObjectMaintenance maintain_world_object(
    WorldObjectMaintenance state,
    const std::function<WorldObjectMotion(WorldObjectMotion)>& update_motion);
std::vector<WorldObjectMaintenance> maintain_world_objects(
    const std::vector<WorldObjectMaintenance>& objects,
    const std::function<WorldObjectMotion(WorldObjectMotion)>& update_motion);
}
