#include "mco/wind.hpp"
#include <iomanip>
#include <iostream>

int main() {
    std::cout<<std::setprecision(17);
    mco::WindState state{};
    while(std::cin>>state.simulation_counter) {
        if(!(std::cin>>state.weather_seed)) return 2;
        for(auto& value:state.track_direction) if(!(std::cin>>value)) return 2;
        for(auto& value:state.world_to_body) if(!(std::cin>>value)) return 2;
        if(!(std::cin>>state.disabled)) return 2;
        const auto out=mco::calculate_wind(state);
        for(auto value:out.body_velocity) std::cout<<value<<' ';
        std::cout<<out.present<<'\n';
    }
}
