#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/raster_scene.hpp"
namespace mco {
// Original 0x483450; cdecl call from 0x53a1f0 with owner and constructor arg.
float scene_area(std::uint32_t owner, std::uint32_t vehicle_index);
// Portable body of the area query over decoded surface records.
float scene_area_from_geometry(std::span<const RasterMesh> meshes,
                               bool raster_enabled = true);
float scene_area_from_nodes(std::span<const RasterSceneNode> nodes,
                            bool raster_enabled = true);
}
