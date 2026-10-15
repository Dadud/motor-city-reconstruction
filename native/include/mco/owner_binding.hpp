#pragma once
#include <array>
#include <cstddef>
#include <span>
namespace mco {
std::array<float,3> body_inertia_scales(int shape,std::array<float,3> initial={1,1,1});
struct OwnerInertia {
    float mass,inverse_mass;
    std::array<float,3> half_extents,shape_scales,inertia,inverse_inertia;
};
struct AxleLevers {float front,rear;};
struct StartupCOMCoordinates {float vertical,longitudinal;};
struct FinalizedOwnerBinding {OwnerInertia inertia;AxleLevers axle_levers;};
OwnerInertia bind_owner_inertia(float mass,std::array<float,3> half_extents,int shape);
AxleLevers bind_axle_levers(float wheelbase,float assembled_front_weight_fraction);
StartupCOMCoordinates bind_startup_com(float height_parameter,float half_height,
    float observed_front_marker_z,float observed_front_lever);
FinalizedOwnerBinding bind_finalized_owner(std::span<const std::byte> configuration,
    std::array<float,3> half_extents,bool assembly_finalized);
}
