#pragma once
#include <array>
namespace mco {
struct ForceOrientationWheel {
    double steering_angle, phase_angle, lateral_force, longitudinal_force;
};
std::array<ForceOrientationWheel,4> orient_wheel_forces(std::array<ForceOrientationWheel,4> wheels,
    double front_parameter,double rear_parameter);
}
