#include "mco/raster_triangle.hpp"
#include <bit>
#include <cstdint>
#include <iostream>

int main() {
    std::array<std::uint32_t,6> bits{};
    while(std::cin>>std::hex>>bits[0]>>bits[1]>>bits[2]>>bits[3]>>bits[4]>>bits[5]) {
        const mco::RasterTriangle input{{{{std::bit_cast<float>(bits[0]),std::bit_cast<float>(bits[1])}},
                                         {{std::bit_cast<float>(bits[2]),std::bit_cast<float>(bits[3])}},
                                         {{std::bit_cast<float>(bits[4]),std::bit_cast<float>(bits[5])}}}};
        const auto out=mco::order_triangle_vertices_by_y(input);
        for(const auto& point:out)
            for(const auto value:point) std::cout<<std::hex<<std::bit_cast<std::uint32_t>(value)<<' ';
        std::cout<<'\n';
    }
}
