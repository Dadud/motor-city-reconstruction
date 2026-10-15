#include "mco/startup_balance.hpp"
#include <array>
#include <bit>
#include <cstdint>
#include <iostream>
#include <stdexcept>
int main() {
    unsigned mode;
    auto read=[]() {std::uint32_t value;if(!(std::cin>>value)) throw std::invalid_argument("incomplete coefficient input");return value;};
    while(std::cin>>mode) {
        if(mode==1) {const auto code=read();std::cout<<std::bit_cast<std::uint32_t>(mco::brake_diameter(code))<<'\n';continue;}
        if(mode==2) {
            const auto diameter=std::bit_cast<float>(read());const auto material=read(),construction=read();
            const auto pressure=std::bit_cast<float>(read());const auto auxiliary=read();
            if(auxiliary>1) throw std::invalid_argument("invalid brake flag");
            std::cout<<std::bit_cast<std::uint64_t>(mco::brake_capacity(diameter,material,construction,pressure,auxiliary!=0))<<'\n';continue;
        }
        if(mode!=0) throw std::invalid_argument("invalid comparison mode");const auto alternate=read();
        if(alternate>1) throw std::invalid_argument("invalid load flag");std::array<std::byte,0x820> config;
        for(unsigned i=0;i<config.size();i+=4) {std::uint32_t value;if(!(std::cin>>value)) throw std::invalid_argument("incomplete configuration");
            for(unsigned k=0;k<4;++k) config[i+k]=static_cast<std::byte>((value>>(k*8))&255);}
        std::cout<<std::bit_cast<std::uint32_t>(mco::startup_load_coefficient(config))<<' '
            <<std::bit_cast<std::uint32_t>(mco::startup_balance_coefficient(config,alternate!=0))<<' '
            <<std::bit_cast<std::uint32_t>(mco::startup_brake_balance(config))<<'\n';
    }
}
