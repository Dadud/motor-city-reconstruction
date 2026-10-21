#include "mco/contact_force.hpp"
#include <array>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string>

int main() {
    unsigned mode{};
    std::string hex;
    while(std::cin>>mode>>hex) {
        if(hex.size()!=0x4f8*2) return 2;
        std::array<std::uint8_t,0x4f8> record{};
        for(std::size_t i=0;i<record.size();++i)
            record[i]=static_cast<std::uint8_t>(std::stoul(hex.substr(i*2,2),nullptr,16));
        if(mode==0) {
            std::array<float,9> input{};
            for(auto& value:input) if(!(std::cin>>value)) return 2;
            const auto result=mco::contact_response(record,
                {input[0],input[1],input[2]},
                {input[3],input[4],input[5]},
                {input[6],input[7],input[8]});
            std::array<std::uint8_t,24> output{};
            std::memcpy(output.data(),result.linear.data(),12);
            std::memcpy(output.data()+12,result.angular.data(),12);
            static constexpr char digits[]="0123456789abcdef";
            for(auto value:output) std::cout<<digits[value>>4]<<digits[value&15];
            std::cout<<'\n';
        } else if(mode==1) {
            mco::contact_forces_step(record);
            static constexpr char digits[]="0123456789abcdef";
            for(auto value:record) std::cout<<digits[value>>4]<<digits[value&15];
            std::cout<<'\n';
        } else return 3;
    }
}
