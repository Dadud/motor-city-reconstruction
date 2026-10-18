#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/free_camera_state.hpp"
namespace mco {
// Original 0x433820; Run original free-camera reset and keyboard update with actual rotation and spatial children.
void free_camera_update(FreeCameraState &state, const TrackSurfaceWorld &world, std::uint32_t event, std::uint32_t reset_time);
}
