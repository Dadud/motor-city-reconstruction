#include "mco/raster_bounds.hpp"
#include <stdexcept>

namespace mco {
RasterBounds occupied_raster_bounds(std::span<const std::uint8_t> bitmap) {
    constexpr std::int32_t width=0x141, height=0xf1;
    if(bitmap.size()!=static_cast<std::size_t>(width*height))
        throw std::invalid_argument("startup occupancy raster must contain exactly 0x141*0xf1 bytes");
    RasterBounds result{1'000'000,1'000'000,-1'000'000,-1'000'000,0};
    for(std::int32_t y=0;y<height;++y) {
        for(std::int32_t x=0;x<width;++x) {
            if(bitmap[static_cast<std::size_t>(y*width+x)]==0) continue;
            if(y<result.min_y) result.min_y=y;
            if(x<result.min_x) result.min_x=x;
            if(x>result.max_x) result.max_x=x;
            if(y>result.max_y) result.max_y=y;
            ++result.count;
        }
    }
    return result;
}
}
