#include "mco/wheel_force_orientation.hpp"
#include <iostream>
#include <iomanip>
int main() {
    std::cout<<std::setprecision(17);
    double front,rear;
    while (std::cin>>front) {
        if (!(std::cin>>rear)) return 2;
        std::array<mco::ForceOrientationWheel,4> wheels{};
        for(auto& w:wheels) if (!(std::cin>>w.steering_angle>>w.phase_angle>>w.lateral_force>>w.longitudinal_force)) return 2;
        const auto out=mco::orient_wheel_forces(wheels,front,rear);
        for(const auto& w:out) std::cout<<w.lateral_force<<' '<<w.longitudinal_force<<' ';
        std::cout<<'\n';
    }
}
