#include "mco/combined_slip.hpp"
#include <iostream>
#include <iomanip>
int main() {
    std::cout<<std::setprecision(17);
    for(std::size_t count=0;count<100000;++count) {
        mco::CombinedSlipState s{};int parking,alternate,contact;
        if(!(std::cin>>s.speed)) return std::cin.eof()?0:2;
        if(!(std::cin>>parking>>alternate>>s.front_quality>>s.rear_quality>>s.vehicle_code)) return 2;
        s.parking_control=parking!=0;s.alternate_mode=alternate!=0;
        for(auto& w:s.wheels) {
            if(!(std::cin>>w.slip_ratio>>w.lateral_force>>w.longitudinal_force>>w.secondary_response>>w.normal_load
                >>w.primary_coefficient>>w.secondary_coefficient>>w.spin_value>>w.spin_scale>>w.projected_speed
                >>contact>>w.component_code>>w.wear_mode)) return 2;
            w.contact=contact!=0;
        }
        const auto out=mco::limit_combined_slip(s);
        for(const auto& w:out.state.wheels) std::cout<<w.lateral_force<<' '<<w.longitudinal_force<<' '<<w.secondary_response<<' ';
        std::cout<<out.effects.size();
        for(const auto& e:out.effects) std::cout<<' '<<e.operation<<' '<<e.slot<<' '<<e.amount<<' '
            <<e.parameter_a<<' '<<e.parameter_b<<' '<<e.parameter_c;
        std::cout<<'\n';
    }
    return 2;
}
