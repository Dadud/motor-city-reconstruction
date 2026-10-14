#include "mco/wheel_force_orientation.hpp"
#include <cmath>
#include <limits>
#include <stdexcept>
namespace mco {
namespace {
double stored(double v) {
    if (!std::isfinite(v) || std::abs(v)>std::numeric_limits<float>::max())
        throw std::invalid_argument("finite float32 force orientation value required");
    return static_cast<float>(v);
}
}
std::array<ForceOrientationWheel,4> orient_wheel_forces(std::array<ForceOrientationWheel,4> wheels,
        double front_parameter,double rear_parameter) {
    const double front=stored(front_parameter),rear=stored(rear_parameter),turn=stored(6.2831855);
    for (int i=0;i<4;++i) {
        auto& w=wheels[i];
        const double steering=stored(w.steering_angle),phase=stored(i*.25+stored(w.phase_angle));
        const double lateral=stored(w.lateral_force),longitudinal=stored(w.longitudinal_force);
        const double angle=stored(steering+std::sin(phase*turn)*(i<2 ? front : rear)*stored(.044444445));
        const double sine=std::sin(angle*turn),cosine=stored(std::cos(angle*turn));
        w.lateral_force=stored(lateral-sine*longitudinal);
        w.longitudinal_force=stored(cosine*longitudinal-sine*lateral);
    }
    return wheels;
}
}
