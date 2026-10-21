#include "mco/raster_rounding.hpp"
#include <bit>
#include <cstdint>
#include <iostream>

int main() {
    std::uint32_t bits{};
    while(std::cin>>std::hex>>bits) {
        const auto value=std::bit_cast<float>(bits);
        std::cout<<std::dec<<mco::raster_ceil(value)<<' '
                 <<mco::raster_floor(value)<<'\n';
    }
}
