#include "mco/world_object_update.hpp"
#include "mco/geometry_transform.hpp"
#include "mco/matrix_math.hpp"
#include <bit>
#include <stdexcept>

namespace mco {
WorldObjectUpdate update_world_object(
    WorldObjectUpdate state, std::uint32_t object_phase,
    const WorldObjectMatrixRepair& repair) {
    if (!state.active) return state;

    std::array<float,3> old_center_world{};
    for (std::size_t axis=0;axis<3;++axis) {
        old_center_world[axis]=static_cast<float>(
            state.center_of_mass[2]*state.rotation[6+axis]+
            state.center_of_mass[1]*state.rotation[3+axis]+
            state.center_of_mass[0]*state.rotation[axis]+state.position[axis]);
    }
    constexpr float dt=0.03125f;
    const std::array<float,3> delta{
        state.angular_velocity[0]*dt,state.angular_velocity[1]*dt,
        state.angular_velocity[2]*dt};
    state.rotation=integrate_rotation_matrix(state.rotation,delta);
    for (std::size_t axis=0;axis<3;++axis) {
        const auto moved=static_cast<float>(state.linear_velocity[axis]*dt+
                                             old_center_world[axis]);
        const auto new_center=static_cast<float>(
            state.center_of_mass[2]*state.rotation[6+axis]+
            state.center_of_mass[1]*state.rotation[3+axis]+
            state.center_of_mass[0]*state.rotation[axis]+state.position[axis]);
        state.position[axis]=static_cast<float>(moved-new_center+state.position[axis]);
    }
    if (((object_phase>>1)&0xffu)==state.object_id) {
        state.rotation=repair ? repair(state.rotation,10)
                              : repair_rotation_matrix(state.rotation,10);
    }
    const auto words=transpose_3x3_words({
        std::bit_cast<std::uint32_t>(state.rotation[0]),
        std::bit_cast<std::uint32_t>(state.rotation[1]),
        std::bit_cast<std::uint32_t>(state.rotation[2]),
        std::bit_cast<std::uint32_t>(state.rotation[3]),
        std::bit_cast<std::uint32_t>(state.rotation[4]),
        std::bit_cast<std::uint32_t>(state.rotation[5]),
        std::bit_cast<std::uint32_t>(state.rotation[6]),
        std::bit_cast<std::uint32_t>(state.rotation[7]),
        std::bit_cast<std::uint32_t>(state.rotation[8])});
    for (std::size_t i=0;i<9;++i) state.transposed_rotation[i]=std::bit_cast<float>(words[i]);
    state.projected={
        dot_3_f32({state.rotation[0],state.rotation[1],state.rotation[2]},state.projection_vector),
        dot_3_f32({state.rotation[3],state.rotation[4],state.rotation[5]},state.projection_vector),
        dot_3_f32({state.rotation[6],state.rotation[7],state.rotation[8]},state.projection_vector)};
    state.world_vertices=transform_world_vertices_22(state.local_vertices,
                                                      state.rotation,state.position);
    return state;
}
}
