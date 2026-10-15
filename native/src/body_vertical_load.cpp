#include "mco/body_vertical_load.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
namespace mco {
namespace {
double f(double x) {
    const double result=static_cast<float>(x);
    if (!std::isfinite(result)) throw std::invalid_argument("finite float required");
    return result;
}
}
BodyVerticalLoadOutput adjust_body_vertical_load(BodyVerticalLoadState s) {
    s.speed=f(s.speed);s.longitudinal_speed=f(s.longitudinal_speed);
    s.front_parameter=f(s.front_parameter);s.rear_parameter=f(s.rear_parameter);
    s.front_speed_parameter=f(s.front_speed_parameter);s.rear_speed_parameter=f(s.rear_speed_parameter);
    s.front_adjustment=f(s.front_adjustment);s.rear_adjustment=f(s.rear_adjustment);
    s.front_quality=f(s.front_quality);s.rear_quality=f(s.rear_quality);
    for(auto& load:s.wheel_loads) load=f(load);
    if(s.speed>=f(8.9406)) {
        s.front_parameter=f(s.front_parameter+s.front_speed_parameter);
        s.rear_parameter=f(s.rear_parameter+s.rear_speed_parameter);
    }
    if(s.front_adjustment!=0) s.front_parameter=f(s.front_parameter*(s.front_parameter>=0?1-s.front_adjustment:1+s.front_adjustment));
    if(s.rear_adjustment!=0) s.rear_parameter=f(s.rear_parameter*(s.rear_parameter>=0?1-s.rear_adjustment:1+s.rear_adjustment));
    const double scale=std::abs(s.longitudinal_speed)*f(4.905);
    const double front=f(scale*s.front_parameter),rear=f(scale*s.rear_parameter);
    for(unsigned i=0;i<4;i++) s.wheel_loads[i]=std::max(0.0,f(s.wheel_loads[i]+(1-(i<2?s.front_quality:s.rear_quality))*(i<2?front:rear)));
    return {front,rear,f(front+rear),s.wheel_loads};
}
}
