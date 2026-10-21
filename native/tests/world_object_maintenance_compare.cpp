#include "mco/world_object_maintenance.hpp"
#include <iomanip>
#include <iostream>

int main() {
    std::cout << std::setprecision(9);
    mco::WorldObjectMaintenance state{};
    int active{};
    while (std::cin >> active >> state.maintenance_value >> state.reference_value) {
        state.active=active!=0;
        if (!(std::cin >> state.motion.contact_counter)) return 2;
        for (auto& value:state.motion.linear_velocity) if (!(std::cin>>value)) return 2;
        for (auto& value:state.motion.angular_velocity) if (!(std::cin>>value)) return 2;
        const auto out=mco::maintain_world_object(state,[](auto value){return value;});
        for (auto value:out.motion.linear_velocity) std::cout<<value<<' ';
        for (auto value:out.motion.angular_velocity) std::cout<<value<<' ';
        std::cout<<'\n';
    }
}
