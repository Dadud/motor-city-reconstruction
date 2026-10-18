#include "mco/startup_record.hpp"
#include <array>
#include <bit>
#include <cstdint>
#include <iostream>
#include <stdexcept>
int main(){
    auto read=[](){std::uint32_t w;if(!(std::cin>>w))throw std::invalid_argument("incomplete startup record input");return w;};
    std::uint32_t has_model;
    while(std::cin>>has_model){
        if(has_model>1)throw std::invalid_argument("unknown startup record mode");
        const auto area=read();
        std::array<std::byte,0x2000> o;std::array<std::byte,0x820> c;
        std::array<std::byte,0x1400> m;
        auto fill=[&](auto& data){for(unsigned i=0;i<data.size();i+=4){auto w=read();for(unsigned k=0;k<4;++k)data[i+k]=static_cast<std::byte>((w>>(k*8))&255);}};
        fill(o);fill(c);fill(m);
        std::array<std::byte,0x4a8> r;
        const bool ok=mco::startup_record(o,c,has_model!=0,m,std::bit_cast<float>(area),r);
        if(!ok){std::cout<<"0\n";continue;}
        std::cout<<"1";
        for(auto v:r)std::cout<<' '<<std::to_integer<unsigned>(v);
        std::cout<<'\n';
    }
}
