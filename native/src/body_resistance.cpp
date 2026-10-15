#include "mco/body_resistance.hpp"
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
BodyResistanceOutput calculate_body_resistance(BodyResistanceState s) {
    s.speed=f(s.speed);s.longitudinal_speed=f(s.longitudinal_speed);s.drag_parameter=f(s.drag_parameter);
    s.drag_adjustment=f(s.drag_adjustment);s.secondary_angle=f(s.secondary_angle);s.area_parameter=f(s.area_parameter);
    s.density=f(s.density);s.wind_lateral=f(s.wind_lateral);s.wind_longitudinal=f(s.wind_longitudinal);
    s.drafting_factor=f(s.drafting_factor);s.pitch_angle=f(s.pitch_angle);s.length_parameter=f(s.length_parameter);
    s.height_parameter=f(s.height_parameter);s.front_lever=f(s.front_lever);s.rear_lever=f(s.rear_lever);
    s.downforce_parameter=f(s.downforce_parameter);s.configuration_downforce=f(s.configuration_downforce);
    for(auto& load:s.wheel_loads) load=f(load);
    if(s.front_lever==0 || s.rear_lever==0) throw std::invalid_argument("nonzero lever required");
    double drag=s.drag_parameter;
    if(s.accessory_parameter && s.accessory_enabled) drag=f(drag+f(.02));
    if(s.drag_adjustment!=0) drag=f(drag*(s.drag_adjustment*.5+1));
    const double rate=s.vehicle_code==6?.003:(s.vehicle_code<=3?.0125:.006);
    const double cap=s.vehicle_code==6?1.12:(s.vehicle_code<=3?1.5:1.24);
    const double lateral=s.vehicle_code==6?6:(s.vehicle_code<=3?10:8);
    const double multiplier=std::min(f(cap),f(std::abs(f(s.secondary_angle*180))*f(rate)+1));
    const double relative=f(std::abs(s.speed)-s.wind_longitudinal);
    double magnitude=s.resistance_disabled?0:f(relative*relative*s.density*s.area_parameter*multiplier*drag*.5);
    magnitude=f(magnitude*s.drafting_factor);
    const double longitudinal=s.longitudinal_speed>=0?-magnitude:magnitude;
    const double yaw=f(s.wind_lateral*s.wind_lateral*lateral*s.density*s.area_parameter*(s.wind_lateral<0?-.5:.5));
    const double moment=(s.height_parameter*f(.9090909)+std::sin(s.pitch_angle*f(6.2831855))*s.length_parameter)*magnitude;
    const double stored_moment=s.resistance_disabled?0:f(moment);
    if(!s.load_transfer_disabled) {
        const double half=moment*.5,front_delta=f(half/s.front_lever);
        for(unsigned i:{0u,1u}) s.wheel_loads[i]=std::max(0.0,f(s.wheel_loads[i]-front_delta));
        const double rear_delta=f(f(half)/s.rear_lever);
        s.wheel_loads[3]=std::max(0.0,f(s.wheel_loads[3]+f(half)/s.rear_lever));
        s.wheel_loads[2]=std::max(0.0,f(s.wheel_loads[2]+rear_delta));
        if(std::all_of(s.contacts.begin(),s.contacts.end(),[](bool contact){return contact;})) {
            const double change=(s.downforce_parameter+s.configuration_downforce)*relative*relative*s.density*s.area_parameter*(-.5)*.25;
            const double stored_change=f(change);
            s.wheel_loads[0]=std::max(0.0,f(s.wheel_loads[0]+change));
            for(unsigned i:{1u,3u,2u}) s.wheel_loads[i]=std::max(0.0,f(s.wheel_loads[i]+stored_change));
        }
    }
    return {longitudinal,yaw,stored_moment,s.wheel_loads};
}
}
