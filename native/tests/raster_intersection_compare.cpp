#include "mco/raster_intersection.hpp"
#include <bit>
#include <cstdint>
#include <iostream>

int main() {
    std::uint32_t bits[9]{};
    while(std::cin>>std::hex>>bits[0]>>bits[1]>>bits[2]>>bits[3]>>bits[4]>>
          bits[5]>>bits[6]>>bits[7]>>bits[8]) {
        const mco::RasterEdge a{{{{std::bit_cast<float>(bits[0]),std::bit_cast<float>(bits[1])}},
                                 {{std::bit_cast<float>(bits[2]),std::bit_cast<float>(bits[3])}}}};
        const mco::RasterEdge b{{{{std::bit_cast<float>(bits[4]),std::bit_cast<float>(bits[5])}},
                                 {{std::bit_cast<float>(bits[6]),std::bit_cast<float>(bits[7])}}}};
        const auto out=mco::raster_scanline_intersections(b,a,std::bit_cast<float>(bits[8]));
        std::cout<<std::hex<<std::bit_cast<std::uint32_t>(out.leftmost_x)<<' '
                 <<std::bit_cast<std::uint32_t>(out.rightmost_x)<<'\n';
    }
}
