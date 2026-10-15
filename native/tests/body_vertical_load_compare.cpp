#include "mco/body_vertical_load.hpp"
#include <iomanip>
#include <iostream>
int main() {
    std::cout<<std::setprecision(17);
    mco::BodyVerticalLoadState s{};
    while(std::cin>>s.speed) {
        if(!(std::cin>>s.longitudinal_speed>>s.front_parameter>>s.rear_parameter>>s.front_speed_parameter
            >>s.rear_speed_parameter>>s.front_adjustment>>s.rear_adjustment>>s.front_quality>>s.rear_quality)) return 2;
        for(auto& load:s.wheel_loads) if(!(std::cin>>load)) return 2;
        const auto out=mco::adjust_body_vertical_load(s);
        std::cout<<out.front_vertical<<' '<<out.rear_vertical<<' '<<out.total_vertical;
        for(auto load:out.wheel_loads) std::cout<<' '<<load;
        std::cout<<'\n';
    }
}
