#include "mco/model_bounds.hpp"
#include <bit>
#include <cstdint>
#include <iostream>
#include <stdexcept>
int main() {
    unsigned mirror,count;
    while(std::cin>>mirror>>count) {
        if(mirror>1 || count>1000000) throw std::invalid_argument("bounded comparison input required");
        mco::FcePart part{};part.vertices.resize(count);
        auto read=[](float& value) {
            std::uint32_t bits;
            if(!(std::cin>>bits)) throw std::invalid_argument("incomplete comparison record");
            value=std::bit_cast<float>(bits);
        };
        for(auto& value:part.origin) read(value);
        for(auto& vertex:part.vertices) for(auto& value:vertex) read(value);
        auto result=mco::transformed_part_bounds(part,mirror!=0);
        if(!result) {std::cout<<"0\n";continue;}
        std::cout<<"1";
        for(float value:result->minimum) std::cout<<' '<<std::bit_cast<std::uint32_t>(value);
        for(float value:result->maximum) std::cout<<' '<<std::bit_cast<std::uint32_t>(value);
        std::cout<<'\n';
    }
}
