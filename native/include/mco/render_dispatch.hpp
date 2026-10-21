#pragma once
#include <cstdint>
#include <functional>

namespace mco {
struct RenderDispatchState {
    const void* matrix_source{};
    const void* position_source{};
    std::uint32_t output_stride_bytes{0x20};
    bool matrix_dirty{};
    bool position_dirty{};
    bool dispatch_cache_valid{true};
};

using GeometryDraw = std::function<void(
    std::uint32_t, std::uint32_t, const void*, void*,
    const void*, const void*, std::uint32_t)>;

void dispatch_object_geometry(
    RenderDispatchState& state, std::uint32_t vertex_count,
    const void* local_vertices, void* world_vertices,
    const void* matrix, const void* position,
    std::uint32_t output_stride_bytes,
    const GeometryDraw& draw);
}
