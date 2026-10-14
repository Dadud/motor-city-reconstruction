#include "mco/brake_thermal.hpp"
#include <iostream>
#include <iomanip>
#include <stdexcept>

int main() {
    std::cout<<std::setprecision(9);
    std::size_t count=0;
    while(true) {
        mco::BrakeThermalState s{};
        int parking,environment;
        if(!(std::cin>>s.service_control))return std::cin.eof()?0:2;
        if(++count>100000||!(std::cin>>parking>>s.speed>>s.mass_parameter>>s.elevation_parameter>>environment>>s.environment_code)
            ||parking<0||parking>1||environment<0||environment>1)return 2;
        s.parking_control=parking!=0;s.environment_flag=environment!=0;
        for(auto* a:{&s.front,&s.rear})
            if(!(std::cin>>a->temperature>>a->diameter>>a->cooling_coefficient>>a->heat_capacity_factor>>a->thermal_mass
                >>a->temperature_limit>>a->material_code>>a->construction_code>>a->countdown))return 2;
        for(auto& w:s.wheels)if(!(std::cin>>w.brake_force>>w.spin_scale>>w.spin_value))return 2;
        try {
            auto r=mco::update_brake_thermal(s);
            std::cout<<r.front.temperature<<' '<<r.rear.temperature<<' '<<r.front.countdown<<' '<<r.rear.countdown
                <<' '<<r.kinetic_value<<' '<<r.elevation_value;
            for(auto& w:r.wheels)std::cout<<' '<<w.brake_force;
            std::cout<<'\n';
        }catch(const std::invalid_argument&){return 3;}
    }
}
