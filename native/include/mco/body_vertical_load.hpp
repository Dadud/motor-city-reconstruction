#pragma once
#include <array>
namespace mco {
struct BodyVerticalLoadState {
    double speed, longitudinal_speed, front_parameter, rear_parameter;
    double front_speed_parameter, rear_speed_parameter, front_adjustment, rear_adjustment;
    double front_quality, rear_quality;
    std::array<double,4> wheel_loads;
};
struct BodyVerticalLoadOutput {
    double front_vertical, rear_vertical, total_vertical;
    std::array<double,4> wheel_loads;
};
BodyVerticalLoadOutput adjust_body_vertical_load(BodyVerticalLoadState state);
}
