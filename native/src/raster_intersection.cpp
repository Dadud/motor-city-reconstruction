#include "mco/raster_intersection.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace mco {
RasterIntersections raster_scanline_intersections(
    RasterEdge a, RasterEdge b, float y) {
    for(const auto& point:a)
        if(!std::isfinite(point[0]) || !std::isfinite(point[1]))
            throw std::invalid_argument("finite float32 edge coordinates required");
    for(const auto& point:b)
        if(!std::isfinite(point[0]) || !std::isfinite(point[1]))
            throw std::invalid_argument("finite float32 edge coordinates required");
    if(!std::isfinite(y))
        throw std::invalid_argument("finite float32 scanline required");
    if(a[0][1]==a[1][1] || b[0][1]==b[1][1])
        throw std::invalid_argument("horizontal edges have undefined intersection");
    // The original evaluates these expressions in x87 extended precision,
    // then stores each result to a 32-bit float before comparing them.
    const float x_a=static_cast<float>(
        ((static_cast<double>(y)-a[0][1])*(static_cast<double>(a[1][0])-a[0][0]))/
        (static_cast<double>(a[1][1])-a[0][1])+a[0][0]);
    const float x_b=static_cast<float>(
        ((static_cast<double>(y)-b[0][1])*(static_cast<double>(b[1][0])-b[0][0]))/
        (static_cast<double>(b[1][1])-b[0][1])+b[0][0]);
    return {std::min(x_a,x_b),std::max(x_a,x_b)};
}
}
