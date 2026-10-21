#include "mco/raster_bounds.hpp"
#include <array>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

int main() {
    std::string hex;
    constexpr std::size_t size=0x141u*0xf1u;
    while(std::cin>>hex) {
        if(hex.size()!=size*2) return 2;
        std::vector<std::uint8_t> bitmap(size);
        for(std::size_t i=0;i<size;++i)
            bitmap[i]=static_cast<std::uint8_t>(std::stoul(hex.substr(i*2,2),nullptr,16));
        const auto b=mco::occupied_raster_bounds(bitmap);
        std::cout<<b.min_x<<' '<<b.min_y<<' '<<b.max_x<<' '<<b.max_y<<' '<<b.count<<'\n';
    }
}
