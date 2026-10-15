#include "mco/body_resistance.hpp"
#include <iomanip>
#include <iostream>
int main() {
    std::cout<<std::setprecision(17);mco::BodyResistanceState s{};
    while(std::cin>>s.speed) {
        if(!(std::cin>>s.longitudinal_speed>>s.drag_parameter>>s.accessory_parameter>>s.accessory_enabled
            >>s.drag_adjustment>>s.vehicle_code>>s.secondary_angle>>s.area_parameter>>s.density
            >>s.wind_lateral>>s.wind_longitudinal>>s.drafting_factor>>s.resistance_disabled
            >>s.pitch_angle>>s.length_parameter>>s.height_parameter>>s.load_transfer_disabled
            >>s.front_lever>>s.rear_lever>>s.downforce_parameter>>s.configuration_downforce)) return 2;
        for(auto& load:s.wheel_loads) if(!(std::cin>>load)) return 2;
        for(unsigned i=0;i<4;i++) {bool contact;if(!(std::cin>>contact)) return 2;s.contacts[i]=contact;}
        const auto out=mco::calculate_body_resistance(s);
        std::cout<<out.longitudinal_drag<<' '<<out.yaw_contribution<<' '<<out.pitch_contribution;
        for(auto load:out.wheel_loads) std::cout<<' '<<load;
        std::cout<<'\n';
    }
}
