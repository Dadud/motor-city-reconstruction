#include "mco/air_density.hpp"
#include <iomanip>
#include <iostream>
int main() {
    double altitude;bool cold,enabled;std::uint32_t weather;
    std::cout<<std::setprecision(17);
    while(std::cin>>altitude) {
        if(!(std::cin>>cold>>enabled>>weather)) return 2;
        std::cout<<mco::calculate_air_density(altitude,cold,enabled,weather)<<'\n';
    }
}
