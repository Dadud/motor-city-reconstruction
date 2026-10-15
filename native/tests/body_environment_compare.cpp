#include "mco/body_environment.hpp"
#include <iomanip>
#include <iostream>

int main() {
    std::cout<<std::setprecision(17);
    mco::BodyResistanceState s{};
    while(std::cin>>s.speed) {
        if(!(std::cin>>s.longitudinal_speed>>s.drag_parameter>>s.accessory_parameter>>s.accessory_enabled
            >>s.drag_adjustment>>s.vehicle_code>>s.secondary_angle>>s.area_parameter>>s.density
            >>s.wind_lateral>>s.wind_longitudinal>>s.drafting_factor>>s.resistance_disabled
            >>s.pitch_angle>>s.length_parameter>>s.height_parameter>>s.load_transfer_disabled
            >>s.front_lever>>s.rear_lever>>s.downforce_parameter>>s.configuration_downforce)) return 2;
        for(auto& v:s.wheel_loads) if(!(std::cin>>v)) return 2;
        for(unsigned i=0;i<4;i++) {bool contact;if(!(std::cin>>contact)) return 2;s.contacts[i]=contact;}
        mco::BodyEnvironment env{};
        if(!(std::cin>>env.altitude>>env.cold_environment>>env.weather_enabled>>env.weather_code
            >>env.wind.simulation_counter>>env.wind.weather_seed)) return 2;
        for(auto& v:env.wind.track_direction) if(!(std::cin>>v)) return 2;
        for(auto& v:env.wind.world_to_body) if(!(std::cin>>v)) return 2;
        unsigned count;
        if(!(std::cin>>env.wind.disabled>>env.current_vehicle>>count) || count>10000) return 2;
        env.vehicles.resize(count);
        for(auto& car:env.vehicles) {
            if(!(std::cin>>car.identifier)) return 2;
            for(auto& v:car.position) if(!(std::cin>>v)) return 2;
            for(auto& v:car.basis) if(!(std::cin>>v)) return 2;
            for(auto& v:car.half_extents) if(!(std::cin>>v)) return 2;
            for(auto& v:car.wake_origin) if(!(std::cin>>v)) return 2;
            for(auto& normal:car.wake_normals) for(auto& v:normal) if(!(std::cin>>v)) return 2;
        }
        const auto out=mco::calculate_body_environment(s,env);
        std::cout<<out.body.longitudinal_drag<<' '<<out.body.yaw_contribution<<' '<<out.body.pitch_contribution;
        for(auto v:out.body.wheel_loads) std::cout<<' '<<v;
        std::cout<<' '<<out.density;
        for(auto v:out.wind.body_velocity) std::cout<<' '<<v;
        std::cout<<' '<<out.wind.present<<' '<<out.drafting.factor<<' '
            <<out.drafting.selected_vehicle.value_or(-1)<<' '<<out.drafting.inside_wake;
        for(const auto& car:out.drafting.vehicles) {
            std::cout<<' '<<car.identifier;
            for(auto v:car.position) std::cout<<' '<<v;
            for(auto v:car.basis) std::cout<<' '<<v;
            for(auto v:car.half_extents) std::cout<<' '<<v;
            for(auto v:car.wake_origin) std::cout<<' '<<v;
            for(auto normal:car.wake_normals) for(auto v:normal) std::cout<<' '<<v;
        }
        std::cout<<'\n';
    }
}
