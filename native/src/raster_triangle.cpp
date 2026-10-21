#include "mco/raster_triangle.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace mco {
RasterTriangle order_triangle_vertices_by_y(RasterTriangle p) {
    for(const auto& point:p)
        if(!std::isfinite(point[0]) || !std::isfinite(point[1]))
            throw std::invalid_argument("finite float32 triangle coordinates required");
    if(p[0][1]<=p[1][1] && p[0][1]<=p[2][1]) {
        if(p[1][1]<p[2][1]) return {p[0],p[1],p[2]};
        return {p[0],p[2],p[1]};
    }
    if(p[1][1]<=p[2][1]) {
        if(p[0][1]<=p[2][1]) return {p[1],p[0],p[2]};
        return {p[1],p[2],p[0]};
    }
    if(p[0][1]<p[1][1]) return {p[2],p[0],p[1]};
    return {p[2],p[1],p[0]};
}
}
