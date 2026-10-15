#include "mco/assembly_weight.hpp"
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
int main() {
    std::cout<<std::setprecision(17);
    std::string line;
    while(std::getline(std::cin,line)) {
        std::istringstream stream(line);
        mco::AssemblyWeightInputs in{};
        if(!(stream>>in.body_mass>>in.body_fraction>>in.wheelbase>>in.shared_mass))
            throw std::runtime_error("invalid weight fixture header");
        for(auto& v:in.front_masses) if(!(stream>>v)) throw std::runtime_error("front mass missing");
        for(auto& v:in.rear_masses) if(!(stream>>v)) throw std::runtime_error("rear mass missing");
        stream>>std::ws;if(!stream.eof()) throw std::runtime_error("trailing weight fixture fields");
        const double result=mco::assembled_front_weight_fraction(in);
        std::cout<<result<<' '<<static_cast<float>(result)<<'\n';
    }
}
