#include "mco/body_constructor.hpp"
#include <bit>
#include <cstdint>
#include <iostream>
#include <stdexcept>
int main() {
    unsigned mode,shape;std::uint32_t identity,material,mass;
    while(std::cin>>mode>>shape>>identity>>material>>mass) {
        std::array<float,3> extents{};
        for(auto& value:extents) {std::uint32_t bits;if(!(std::cin>>bits)) throw std::invalid_argument("incomplete body input");value=std::bit_cast<float>(bits);}
        if(mode>1) throw std::invalid_argument("invalid body comparison mode");
        if(mode==0) {
            const auto points=mco::body_samples(static_cast<mco::BodyShape>(shape),extents);
            for(const auto& point:points) for(auto v:point) std::cout<<std::bit_cast<std::uint32_t>(v)<<' ';
        } else {
            mco::StartupOwnerImage owner{};
            for(unsigned i=0;i<owner.size();++i) owner[i]=static_cast<std::byte>((i*73+19)&255);
            const auto result=mco::construct_body(owner,identity,std::bit_cast<float>(mass),extents,static_cast<mco::BodyShape>(shape),material);
            for(unsigned i=0;i<result.size();i+=4) {
                std::uint32_t word=0;for(unsigned k=0;k<4;++k) word|=std::to_integer<std::uint32_t>(result[i+k])<<(k*8);
                std::cout<<word<<' ';
            }
        }
        std::cout<<'\n';
    }
}
