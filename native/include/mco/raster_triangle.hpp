#pragma once
#include <array>

namespace mco {
using RasterTriangle = std::array<std::array<float,2>,3>;
RasterTriangle order_triangle_vertices_by_y(RasterTriangle vertices);
}
