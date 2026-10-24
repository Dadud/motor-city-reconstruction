#pragma once
#include <array>
namespace mco {
struct NormalLoadInput {
    std::array<bool, 4> support; // LF RF LR RR.
    double pitch, bank, mass, wheelbase, front_track, rear_track, height_parameter;
    double front_lever, rear_lever, speed, curvature_scale, vertical_correction;
    std::array<double, 4> wheel_scales;
};
std::array<float, 4> normal_load(const NormalLoadInput& state);
std::array<std::array<float, 3>, 4> normal_force_vectors(const NormalLoadInput& state);
}
