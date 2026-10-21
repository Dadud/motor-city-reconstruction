#pragma once
#include "mco/fce.hpp"
#include "mco/raster_fill.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

namespace mco {
using RasterVertex3 = std::array<float,3>;
using RasterFace = std::array<std::size_t,3>;
struct RasterMesh {
    std::vector<RasterVertex3> vertices;
    std::vector<RasterFace> faces;
    RasterVertex3 position{};
    std::int32_t mesh_type{};
    bool has_model{true};
    std::int16_t surface_id{};
    std::size_t vertex_base{};
    std::size_t face_base{};
};
struct RasterSceneNode {
    const FceModel* model{};
    std::int16_t surface_id{};
    std::int32_t mesh_type{};
};
std::vector<RasterMesh> raster_meshes_from_nodes(
    std::span<const RasterSceneNode> nodes);
RasterTriangleMask rasterize_scene_geometry(
    std::span<const RasterMesh> meshes,
    float x_min, float x_max, float y_min, float y_max);
}
