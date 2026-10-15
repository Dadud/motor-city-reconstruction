#include "mco/owner_binding.hpp"
#include <bit>
#include <cstdint>
#include <iostream>
#include <stdexcept>
int main() {
    unsigned mode;int shape;
    auto read=[]() {std::uint32_t value;if(!(std::cin>>value)) throw std::invalid_argument("incomplete binding record");return std::bit_cast<float>(value);};
    auto emit=[](float value) {std::cout<<std::bit_cast<std::uint32_t>(value)<<' ';};
    while(std::cin>>mode>>shape) {
        if(mode==0) {
            auto mass=read();std::array<float,3> extents{read(),read(),read()};
            auto r=mco::bind_owner_inertia(mass,extents,shape);emit(r.mass);emit(r.inverse_mass);
            for(auto v:r.half_extents) emit(v);for(auto v:r.shape_scales) emit(v);
            for(auto v:r.inertia) emit(v);for(auto v:r.inverse_inertia) emit(v);
        } else if(mode==1) {const auto wheelbase=read(),fraction=read();auto r=mco::bind_axle_levers(wheelbase,fraction);emit(r.front);emit(r.rear);}
        else if(mode==2) {const auto height=read(),half=read(),marker=read(),lever=read();auto r=mco::bind_startup_com(height,half,marker,lever);emit(r.vertical);emit(r.longitudinal);}
        else if(mode==3) {const std::array<float,3> initial{read(),read(),read()};for(auto v:mco::body_inertia_scales(shape,initial)) emit(v);}
        else throw std::invalid_argument("invalid binding mode");
        std::cout<<'\n';
    }
}
