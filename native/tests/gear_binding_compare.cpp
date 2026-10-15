#include "mco/gear_binding.hpp"
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
int main() {
    std::cout<<std::setprecision(17);
    std::string line;
    while(std::getline(std::cin,line)) {
        std::istringstream in(line);
        std::int32_t rpm;double width,aspect,rim,final;std::size_t count;
        if(!(in>>rpm>>width>>aspect>>rim>>final>>count) || count>8)
            throw std::runtime_error("invalid gear fixture header");
        std::vector<double> ratios(count),losses(count);
        for(auto* values:{&ratios,&losses}) for(auto& value:*values)
            if(!(in>>value)) throw std::runtime_error("invalid gear fixture table");
        in>>std::ws;if(!in.eof()) throw std::runtime_error("trailing gear fixture fields");
        const auto result=mco::bind_gear_tables(rpm,width,aspect,rim,ratios,losses,final);
        for(const auto* table:{&result.rpm_per_speed,&result.speed_per_rpm,&result.loss_final_ratio,
            &result.wheel_inertia_factors,&result.inverse_near_limit_speed})
            for(double value:*table) std::cout<<value<<' ';
        std::cout<<result.final_drive_inertia<<'\n';
    }
}
