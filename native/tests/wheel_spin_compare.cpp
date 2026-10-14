#include "mco/wheel_spin.hpp"
#include <iostream>
#include <iomanip>
int main() {
    std::cout<<std::setprecision(17);
    for(std::size_t count=0;count<100000;++count) {
        mco::WheelSpinState s{};int mode,override,correction,contact;
        if(!(std::cin>>mode)) return std::cin.eof()?0:2;
        if(mode<0 || mode>255 || !(std::cin>>override>>s.rpm>>s.gear_multiplier>>s.front_scale>>s.rear_scale
            >>s.front_compliance>>s.rear_compliance>>s.front_secondary_angle>>s.rear_secondary_angle
            >>s.front_quality>>s.rear_quality>>s.body_secondary_angle>>s.front_lever>>s.rear_lever>>s.yaw_rate>>s.lateral_velocity)) return 2;
        s.direction_mode=static_cast<std::uint8_t>(mode);s.override_control=override!=0;
        for(auto& w:s.wheels) {
            if(!(std::cin>>w.spin_value>>w.spin_adjustment>>w.spin_scale>>w.projected_speed>>w.normal_load
                >>w.kinetic_parameter>>w.ratio_denominator>>w.phase>>correction>>contact>>w.secondary_angle
                >>w.slip_ratio>>w.kinetic_value>>w.local_lateral>>w.local_vertical>>w.local_longitudinal)) return 2;
            w.correction_enabled=correction!=0;w.contact=contact!=0;
        }
        const auto out=mco::integrate_wheel_spin(s);
        for(const auto& w:out.state.wheels) std::cout<<w.spin_value<<' '<<w.spin_scale<<' '<<w.phase<<' '
            <<w.secondary_angle<<' '<<w.slip_ratio<<' '<<w.kinetic_value<<' '<<w.local_lateral<<' '
            <<w.local_vertical<<' '<<w.local_longitudinal<<' ';
        std::cout<<out.wear_events.size();
        for(const auto& [slot,amount]:out.wear_events) std::cout<<' '<<slot<<' '<<amount;
        std::cout<<'\n';
    }
    return 2;
}
