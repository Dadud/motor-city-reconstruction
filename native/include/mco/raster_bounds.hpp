#pragma once
#include <cstdint>
#include <span>

namespace mco {
struct RasterBounds {
    std::int32_t min_x, min_y, max_x, max_y, count;
};

RasterBounds occupied_raster_bounds(std::span<const std::uint8_t> bitmap);
}
