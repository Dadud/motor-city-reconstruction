#include "mco/raster_rounding.hpp"
#include <cmath>
#include <limits>
#include <stdexcept>

namespace mco {
namespace {
void validate(float value) {
    if(!std::isfinite(value) || value < -2147483648.0f || value >= 2147483648.0f)
        throw std::invalid_argument("finite float32 value with int32-rounded result required");
}
}
std::int32_t raster_ceil(float value) {
    validate(value);
    return static_cast<std::int32_t>(std::ceil(value));
}
std::int32_t raster_floor(float value) {
    validate(value);
    return static_cast<std::int32_t>(std::floor(value));
}
}
