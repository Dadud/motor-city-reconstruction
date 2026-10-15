#include "mco/wind.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace mco {
namespace {
double f(double value) {
    const double stored=static_cast<float>(value);
    if(!std::isfinite(stored)) throw std::invalid_argument("finite float32 value required");
    return stored;
}
constexpr double tau=6.2831854820251465;
constexpr double inverse_tau=0.15915493667125702;
}
WindOutput calculate_wind(WindState s) {
    for(auto& value:s.track_direction) value=f(value);
    for(auto& value:s.world_to_body) value=f(value);
    if(s.disabled) return {{0.,0.,0.},false};
    const double time=f(s.simulation_counter*.015625);
    const double first_phase=f(time*f(.033333335));
    const double second_phase=f(time*f(.026666667));
    const double first_sine=std::sin(first_phase*tau);
    const double second_sine=f(std::sin(second_phase*tau));
    const double offset=f((s.weather_seed%360)*f(.0027777778));
    double angle=f(std::atan2(s.track_direction[0],s.track_direction[2])*inverse_tau+offset);
    angle=f(first_sine*second_sine*f(.055555556)+angle);
    const int base=std::clamp(s.weather_seed%15,3,15);
    const double magnitude=f(base*f(.44703)+first_sine*second_sine*f(1.117575));
    const double x=f(std::sin(angle*tau)*magnitude);
    const double z=f(std::cos(angle*tau)*magnitude);
    WindOutput out{{},magnitude!=0.};
    for(unsigned i=0;i<3;i++)
        out.body_velocity[i]=f((x*s.world_to_body[i]+0.*s.world_to_body[i+3])+z*s.world_to_body[i+6]);
    return out;
}
}
