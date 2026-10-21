#pragma once
#include <array>

namespace mco {
using RasterEdge = std::array<std::array<float,2>,2>;
struct RasterIntersections {
    float leftmost_x;
    float rightmost_x;
};
RasterIntersections raster_scanline_intersections(
    RasterEdge edge_a, RasterEdge edge_b, float scan_y);
}
