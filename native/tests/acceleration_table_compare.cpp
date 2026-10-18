#include "mco/acceleration_table.hpp"
#include <array>
#include <bit>
#include <cstdint>
#include <iostream>
#include <stdexcept>
int main(){
    unsigned mode;auto read=[](){std::uint32_t w;if(!(std::cin>>w))throw std::invalid_argument("incomplete acceleration input");return w;};
    while(std::cin>>mode){
        const auto rpm=read(),selector=read(),sample=read(),secondary=read();
        std::array<std::byte,0x820> c;std::array<std::byte,0x4a8> r;
        auto fill=[&](auto& data){for(unsigned i=0;i<data.size();i+=4){auto w=read();for(unsigned k=0;k<4;++k)data[i+k]=static_cast<std::byte>((w>>(k*8))&255);}};
        fill(c);fill(r);
        if(mode==1){std::cout<<std::bit_cast<std::uint64_t>(mco::startup_force(c,r,std::bit_cast<std::int32_t>(rpm),selector,std::bit_cast<float>(sample),secondary!=0))<<'\n';continue;}
        if(mode!=0)throw std::invalid_argument("unknown acceleration mode");
        const auto result=mco::acceleration_table(c,r);
        for(auto v:result)std::cout<<std::to_integer<unsigned>(v)<<' ';std::cout<<'\n';
    }
}
