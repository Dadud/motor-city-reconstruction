#include "mco/world_object_physics_step.hpp"
#include "mco/contact_force.hpp"
#include <array>
#include <cstdint>
#include <iostream>
#include <string>

int main() {
    unsigned mode_active{},mode_number{};
    std::string hex;
    while(std::cin>>mode_active>>mode_number>>hex) {
        if(hex.size()!=mco::world_object_record_size*2) return 2;
        std::array<std::uint8_t,mco::world_object_record_size> bytes{};
        for(std::size_t i=0;i<bytes.size();++i) {
            const auto part=hex.substr(i*2,2);
            bytes[i]=static_cast<std::uint8_t>(std::stoul(part,nullptr,16));
        }
        mco::step_world_object_physics(bytes,mode_active!=0,mode_number,
            [](auto){},[](auto record){mco::contact_forces_step(record);});
        static constexpr char digits[]="0123456789abcdef";
        for(auto value:bytes) std::cout<<digits[value>>4]<<digits[value&15];
        std::cout<<'\n';
    }
}
