#include "mco/brake_forces.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
namespace mco {
namespace {
double stored(double v) {
    if (!std::isfinite(v) || std::abs(v)>std::numeric_limits<float>::max())
        throw std::invalid_argument("finite float32 brake value required");
    return static_cast<float>(v);
}
}
BrakeForceOutput update_brake_forces(BrakeForceState s) {
    if(s.parking_ramp<0 || s.parking_ramp>64) throw std::invalid_argument("parking ramp in [0,64] required");
    for (double* v:{&s.front_quality,&s.rear_quality,&s.front_gate,&s.rear_distribution,&s.drive_factor,&s.pitch_angle}) *v=stored(*v);
    for (int i=0;i<4;++i) {
        auto& w=s.wheels[i];
        for(double* v:{&w.spin_value,&w.spin_adjustment,&w.spin_scale,&w.projected_speed,&w.normal_load,
            &w.longitudinal_force,&w.control_angle,&w.inertia_addend,&w.inertia_multiplier}) *v=stored(*v);
        if(w.spin_scale<=0 || w.normal_load<0) throw std::invalid_argument("positive scale and nonnegative load required");
        s.thermal.wheels[i].spin_scale=w.spin_scale;s.thermal.wheels[i].spin_value=w.spin_value;
    }
    s.thermal=update_brake_thermal(s.thermal);
    const double service=s.thermal.service_control,speed=std::abs(s.thermal.speed);
    std::array<double,4> forces{};
    std::array<bool,4> enabled{true,true,true,true};
    BrakeForceOutput out{};
    if(service!=0 || s.thermal.parking_control || s.auxiliary_flag) {
        for(int i=0;i<4;++i) {
            auto& w=s.wheels[i];const auto& axle=i<2 ? s.thermal.front : s.thermal.rear;
            double strength=0;
            if(service!=0) {
                const double cold=axle.material_code==3 && axle.temperature<160 ? stored(.8) : 1;
                if(axle.temperature>axle.temperature_limit)
                    out.wear_events.emplace_back(i,stored((axle.temperature-axle.temperature_limit)*stored(2.6041666e-6)));
                const double fade=brake_fade(axle.temperature,axle.temperature_limit);
                const double quality=std::min(i<2 ? s.front_quality : s.rear_quality,.5);
                strength=stored((1-quality)*fade*cold*service);
            }
            if(strength==0 && !s.thermal.parking_control && !s.auxiliary_flag) {enabled.fill(false);continue;}
            const double motion=stored(w.spin_value*32+w.spin_adjustment);
            double inertia=stored(s.drive_factor*w.inertia_multiplier*.5+w.inertia_addend);
            if(inertia==0) throw std::invalid_argument("nonzero derived inertia required");
            const double drag=std::abs(stored(inertia*w.spin_adjustment));
            const bool special=w.component_code==6 || w.component_code==20 || s.vehicle_code==1;
            const double radius=stored(axle.diameter*.5);
            const double material=stored(axle.material_code==0 ? .85 : axle.material_code==1 ? .9 : axle.material_code==2 ? .95 : 1);
            double capacity=stored(material*radius*radius*stored(3.1415927)*stored(16.310127)*2500
                *(i<2 ? strength : !s.thermal.parking_control && !s.auxiliary_flag ? s.rear_distribution*strength : 1));
            if(axle.construction_code==1) {capacity=stored(capacity*stored(.98));if(special) capacity=stored(capacity*stored(.8));}
            const bool parking=i>=2 && (s.thermal.parking_control || s.auxiliary_flag);
            double adjustment=0;
            if(parking) {
                s.parking_ramp=std::min(s.parking_ramp+4,64);
                inertia=w.inertia_addend;
                if(inertia==0) throw std::invalid_argument("nonzero parking inertia required");
                const double signed_capacity=w.projected_speed>0 ? -capacity : capacity;
                forces[i]=stored(signed_capacity/w.spin_scale);
                const double available=stored(std::abs(motion)*inertia);
                const double torque=w.projected_speed<=0 ? std::min(available,signed_capacity) : std::max(-available,signed_capacity);
                adjustment=stored(torque/inertia);
            } else {
                double torque=capacity;
                if(speed>1) {
                    const double reduction=std::min(drag,stored(capacity*.5));
                    if(std::abs(w.spin_value)<stored(.05)) torque=stored(capacity-reduction);
                } else {
                    const double cosine=std::cos(s.pitch_angle*stored(6.2831855));
                    if(cosine==0) throw std::invalid_argument("nonzero pitch cosine required");
                    const double stationary=stored(s.thermal.mass_parameter*stored(.00066666666)*(stored(i<2 ? .12 : .082)/cosine)*capacity);
                    const double rolling=stored(w.normal_load*w.spin_scale*speed*strength*stored(3.2619774));
                    torque=i<2 ? std::max(std::abs(stationary),rolling) : std::abs(std::max(stationary,rolling));
                }
                const bool gate=i<2 ? s.front_gate!=0 : s.rear_gate!=0;
                if(!gate || w.control_angle>stored(-.4)) {
                    forces[i]=stored(torque/w.spin_scale);adjustment=stored(torque/inertia);
                    if(axle.material_code==2 || axle.material_code==3)
                        out.controller_events.push_back(static_cast<int>(std::nearbyint(stored(strength*(i>=2 && axle.material_code==2 ? 64 : 127)))));
                } else {enabled[i]=false;adjustment=0;}
                if(i>=2) s.parking_ramp=0;
            }
            const double limit=std::abs(motion);
            adjustment=std::clamp(adjustment,-limit,limit);
            adjustment=w.spin_value<=0 ? std::min(std::abs(adjustment),stored(w.spin_value*-32))
                : std::max(-std::abs(adjustment),stored(w.spin_value*-32));
            if(s.front_gate!=0 && (!enabled[0] || !enabled[1])) enabled[0]=enabled[1]=false;
            if(s.rear_gate!=0 && (!enabled[2] || !enabled[3])) enabled[2]=enabled[3]=false;
            if(speed<=1) forces[i]=stored(-(w.projected_speed*s.thermal.mass_parameter)*8);
            const bool gate=i<2 ? s.front_gate!=0 : s.rear_gate!=0;
            if(!gate || enabled[i]) {
                w.spin_adjustment=stored(w.spin_adjustment+adjustment*(gate ? .25 : .5));
                if(w.normal_load!=0) w.longitudinal_force=stored(w.longitudinal_force+(w.projected_speed<=0 ? std::abs(forces[i]) : -std::abs(forces[i])));
            }
        }
    }
    for(int i=0;i<4;++i) s.thermal.wheels[i].brake_force=forces[i];
    out.state=s;return out;
}
}
