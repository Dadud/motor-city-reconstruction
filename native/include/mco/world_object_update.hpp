#pragma once
#include <array>
#include <cstdint>
#include <functional>

namespace mco {
struct WorldObjectUpdate {
    std::uint32_t object_id{};
    bool active{};
    std::array<float,3> position{};
    std::array<float,3> linear_velocity{};
    std::array<float,3> center_of_mass{};
    std::array<float,9> rotation{};
    std::array<float,3> angular_velocity{};
    std::array<float,3> projection_vector{};
    std::array<float,66> local_vertices{};
    std::array<float,66> world_vertices{};
    std::array<float,3> projected{};
    std::array<float,9> transposed_rotation{};
};

using WorldObjectMatrixRepair = std::function<std::array<float,9>(
    const std::array<float,9>&, int)>;
WorldObjectUpdate update_world_object(
    WorldObjectUpdate state, std::uint32_t object_phase,
    const WorldObjectMatrixRepair& repair = {});
}
