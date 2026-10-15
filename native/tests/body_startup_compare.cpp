#include "mco/body_constructor.hpp"
#include <bit>
#include <cstdint>
#include <iostream>
#include <stdexcept>
int main() {
    std::uint32_t identity;
    while(std::cin>>identity) {
        auto read=[]() {std::uint32_t value;if(!(std::cin>>value)) throw std::invalid_argument("incomplete startup input");return value;};
        std::array<float,3> extents{std::bit_cast<float>(read()),std::bit_cast<float>(read()),std::bit_cast<float>(read())};
        auto fill=[&](auto& image) {
            for(unsigned i=0;i<image.size();i+=4) {const auto value=read();for(unsigned k=0;k<4;++k) image[i+k]=static_cast<std::byte>((value>>(k*8))&255);}
        };
        mco::StartupOwnerImage owner;std::array<std::byte,0x820> config;fill(owner);fill(config);
        auto out=mco::prepare_startup_body(owner,config,extents,identity,true);
        for(unsigned i=0;i<out.size();i+=4) {
            std::uint32_t value=0;for(unsigned k=0;k<4;++k) value|=std::to_integer<std::uint32_t>(out[i+k])<<(k*8);
            std::cout<<value<<' ';
        }
        std::cout<<'\n';
    }
}
