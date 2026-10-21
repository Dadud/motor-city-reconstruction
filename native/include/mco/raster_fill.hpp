#pragma once
#include "mco/raster_triangle.hpp"
#include <array>
#include <cstddef>
#include <cstdint>

namespace mco {
inline constexpr std::size_t raster_width = 321;
inline constexpr std::size_t raster_height = 241;
using RasterTriangleMask = std::array<std::uint8_t,raster_width*raster_height>;
RasterTriangleMask rasterize_projected_triangle(
    RasterTriangle vertices, float x_min, float x_max, float y_min, float y_max);
}
