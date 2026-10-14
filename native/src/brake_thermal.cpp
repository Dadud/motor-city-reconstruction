#include "mco/brake_thermal.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace mco {
namespace {
double stored(double v) {
    if(!std::isfinite(v)||std::abs(v)>std::numeric_limits<float>::max())
        throw std::invalid_argument("finite float32 brake observation required");
    return static_cast<float>(v);
}
}
std::int32_t brake_countdown(double diameter,std::uint32_t material,std::uint32_t construction) {
    const double value=stored(stored(diameter)*stored(39.370098));
    const double floor=std::floor(value),fraction=value-floor;
    const double rounded=fraction<.5?floor:(fraction>.5?floor+1:(std::fmod(floor,2)==0?floor:floor+1));
    const double total=rounded+(material==1?16:material==2?8:material==3?32:0)+(construction==1?8:0);
    if(total<std::numeric_limits<std::int32_t>::min()||total>std::numeric_limits<std::int32_t>::max())
        throw std::invalid_argument("countdown outside signed range");
    return static_cast<std::int32_t>(total);
}
double brake_fade(double temperature,double limit) {
    temperature=stored(temperature);limit=stored(limit);
    if(temperature<limit)return 1;
    if(limit+50<temperature)return .5;
    return std::clamp(stored((limit-temperature)*stored(.01)+1),.5,1.0);
}
double brake_ambient(bool flag,std::int32_t code) {return (flag?5:15)-(code==1?10:code==2?20:0);}
BrakeThermalState update_brake_thermal(BrakeThermalState s) {
    s.service_control=stored(s.service_control);s.speed=stored(s.speed);
    s.mass_parameter=stored(s.mass_parameter);s.elevation_parameter=stored(s.elevation_parameter);
    for(auto& w:s.wheels) {w.brake_force=stored(w.brake_force);w.spin_scale=stored(w.spin_scale);w.spin_value=stored(w.spin_value);}
    double front=0,rear=0;
    if((s.service_control!=0||s.parking_control)&&std::abs(s.speed)>1) {
        if(s.service_control!=0)
            front=stored((std::abs(stored(s.wheels[0].brake_force*s.wheels[0].spin_scale*s.wheels[0].spin_value))+
                std::abs(stored(s.wheels[1].brake_force*s.wheels[1].spin_scale*s.wheels[1].spin_value)))*.03125);
        const double first=std::abs(stored(s.wheels[2].spin_scale*s.wheels[2].spin_value));
        const double second=std::abs(stored(s.wheels[3].spin_scale*s.wheels[3].spin_value));
        if(s.parking_control||(s.service_control!=0&&std::max(first,second)>1))
            rear=stored((std::abs(stored(first*s.wheels[2].brake_force))+
                std::abs(stored(second*s.wheels[3].brake_force)))*.03125);
    }
    const double ambient=brake_ambient(s.environment_flag,s.environment_code);
    for(std::size_t i=0;i<2;++i) {
        auto& a=i==0?s.front:s.rear;
        for(double* v:{&a.temperature,&a.diameter,&a.cooling_coefficient,&a.heat_capacity_factor,&a.thermal_mass,&a.temperature_limit})*v=stored(*v);
        if(a.heat_capacity_factor<=0||a.thermal_mass<=0||a.countdown<0)
            throw std::invalid_argument("positive thermal denominators and nonnegative countdown required");
        if(s.service_control==0) {
            const auto count=brake_countdown(a.diameter,a.material_code,a.construction_code);
            if(count>std::numeric_limits<std::int32_t>::max()-64)throw std::invalid_argument("countdown overflow");
            a.countdown=count+64;
        } else a.countdown=std::max(0,a.countdown-1);
        const double cooling=(a.temperature-ambient)*a.diameter*a.diameter*.25*stored(3.1415927)*
            a.cooling_coefficient*stored(std::abs(s.speed)+5);
        a.temperature=std::min(stored(a.temperature+((i==0?front:rear)-cooling)*stored(.001)/
            ((a.thermal_mass+a.thermal_mass)*a.heat_capacity_factor)),stored(a.temperature_limit+a.temperature_limit));
    }
    for(auto& w:s.wheels)w.brake_force=0;
    s.kinetic_value=stored(s.speed*s.speed*s.mass_parameter*.5);
    s.elevation_value=stored(s.mass_parameter*s.elevation_parameter*stored(9.81));
    return s;
}
}
