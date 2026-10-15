#include "mco/drafting.hpp"
#include <iomanip>
#include <iostream>

int main() {
    std::cout<<std::setprecision(17);
    std::int64_t identifier;
    while(std::cin>>identifier) {
        unsigned count;
        if(!(std::cin>>count) || count>10000) return 2;
        std::vector<mco::DraftVehicle> cars(count);
        for(auto& car:cars) {
            if(!(std::cin>>car.identifier)) return 2;
            for(auto& v:car.position) if(!(std::cin>>v)) return 2;
            for(auto& v:car.basis) if(!(std::cin>>v)) return 2;
            for(auto& v:car.half_extents) if(!(std::cin>>v)) return 2;
            for(auto& v:car.wake_origin) if(!(std::cin>>v)) return 2;
            for(auto& normal:car.wake_normals) for(auto& v:normal) if(!(std::cin>>v)) return 2;
        }
        const auto out=mco::calculate_drafting(identifier,std::move(cars));
        std::cout<<out.factor<<' '<<out.selected_vehicle.value_or(-1)<<' '<<out.inside_wake;
        for(const auto& car:out.vehicles) {
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
