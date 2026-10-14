#include "mco/wheel_force_correction.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace mco {
namespace {
double stored(double value) {
    if (!std::isfinite(value) || std::abs(value)>std::numeric_limits<float>::max())
        throw std::invalid_argument("finite float32 wheel observation required");
    return static_cast<float>(value);
}
}
std::array<ForceCorrectionWheel,4> correct_wheel_forces(
    std::array<ForceCorrectionWheel,4> wheels, double service_control,
    double other_control, bool parking_control, std::uint8_t direction_mode,
    bool override_control) {
    const double service=stored(service_control), other=stored(other_control);
    for (std::size_t i=0;i<wheels.size();++i) {
        auto& w=wheels[i];
        for(double* value : {&w.projected_speed,&w.spin_value,&w.spin_adjustment,
                &w.spin_scale,&w.lateral_force,&w.longitudinal_force,&w.normal_load,
                &w.primary_coefficient,&w.secondary_coefficient}) *value=stored(*value);
        if(w.spin_scale<=0 || w.normal_load<0 || w.primary_coefficient<0 || w.secondary_coefficient<0)
            throw std::invalid_argument("positive scale and nonnegative load/coefficients required");
        if(w.normal_load!=0 && w.contact) {
            const double mismatch=stored(-((w.spin_value-w.projected_speed/w.spin_scale)*32+w.spin_adjustment));
            const double stop=stored(-(w.spin_value*32+w.spin_adjustment));
            const double magnitude=stored(std::sqrt(w.lateral_force*w.lateral_force+w.longitudinal_force*w.longitudinal_force));
            const double capacity=stored(w.primary_coefficient*w.normal_load);
            const double secondary=stored(w.secondary_coefficient*w.normal_load);
            const double residual=stored(capacity-std::abs(w.longitudinal_force));
            const double lower=stored(secondary*stored(.15));
            const double limited=std::max(lower,std::min(capacity,residual));
            if(magnitude>capacity)
                w.spin_adjustment=stored(w.spin_adjustment+std::max(0.0,stored(secondary-std::abs(w.longitudinal_force)))*mismatch/magnitude);
            else if((((service>0)||(i>=2 && parking_control)) && w.longitudinal_force<0)
                    || (other>0 && w.longitudinal_force>0)) {
                if(capacity==0) throw std::invalid_argument("nonzero correction capacity required");
                w.spin_adjustment=stored(w.spin_adjustment+limited*mismatch/capacity);
            } else w.spin_adjustment=stored(w.spin_adjustment+mismatch);
            if(w.correction_enabled) {
                if(direction_mode>=2 && !override_control && w.spin_adjustment<stop) w.spin_adjustment=stop;
                else if(direction_mode==0 && w.spin_adjustment>stop) w.spin_adjustment=stop;
            }
        } else if(w.longitudinal_force==0) w.spin_value=stored(w.spin_value*stored(.999375));
    }
    return wheels;
}
}
