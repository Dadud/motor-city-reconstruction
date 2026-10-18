#include "mco/gear_force_table.hpp"
#include <array>
#include <bit>
#include <cstdint>
#include <iostream>
#include <stdexcept>
int main() {
    unsigned selector;
    auto read=[]() {std::uint32_t v;if(!(std::cin>>v))throw std::invalid_argument("incomplete gear force input");return v;};
    while(std::cin>>selector) {
        std::array<float,8> steps;for(auto& v:steps)v=std::bit_cast<float>(read());
        std::array<std::byte,0x820> config;
        for(unsigned i=0;i<config.size();i+=4){const auto word=read();for(unsigned k=0;k<4;++k)config[i+k]=static_cast<std::byte>((word>>(k*8))&255);}
        const auto result=mco::gear_force_table(config,steps,selector);
        for(auto v:result)std::cout<<std::bit_cast<std::uint32_t>(v)<<' ';std::cout<<'\n';
    }
}
