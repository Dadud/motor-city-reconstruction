#include "mco/raster_fill.hpp"
#include <bit>
#include <cstdint>
#include <iostream>

int main() {
    std::uint32_t w[10]{};
    while(std::cin>>std::hex>>w[0]>>w[1]>>w[2]>>w[3]>>w[4]>>w[5]>>
          w[6]>>w[7]>>w[8]>>w[9]) {
        const mco::RasterTriangle p{{{{std::bit_cast<float>(w[0]),std::bit_cast<float>(w[1])}},
                                     {{std::bit_cast<float>(w[2]),std::bit_cast<float>(w[3])}},
                                     {{std::bit_cast<float>(w[4]),std::bit_cast<float>(w[5])}}}};
        const auto mask=mco::rasterize_projected_triangle(
            p,std::bit_cast<float>(w[6]),std::bit_cast<float>(w[7]),
            std::bit_cast<float>(w[8]),std::bit_cast<float>(w[9]));
        static constexpr char digits[]="0123456789abcdef";
        for(const auto value:mask) {
            std::cout<<digits[value>>4]<<digits[value&0xf];
        }
        std::cout<<'\n';
    }
}
