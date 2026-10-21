#include "mco/render_dispatch.hpp"
#include <stdexcept>

namespace mco {
void dispatch_object_geometry(
    RenderDispatchState& state, std::uint32_t vertex_count,
    const void* local_vertices, void* world_vertices,
    const void* matrix, const void* position,
    std::uint32_t output_stride_bytes,
    const GeometryDraw& draw) {
    if (!draw) throw std::invalid_argument("the graphics draw callback is required");
    const auto old_matrix=state.matrix_source;
    const auto old_position=state.position_source;
    const auto old_stride=state.output_stride_bytes;
    const auto set_matrix=[&](const void* value) {
        state.matrix_source=value;
        if(value) state.matrix_dirty=true;
        else state.dispatch_cache_valid=false;
    };
    const auto set_position=[&](const void* value) {
        state.position_source=value;
        if(value) state.position_dirty=true;
        else state.dispatch_cache_valid=false;
    };
    try {
        set_matrix(matrix);
        set_position(position);
        state.output_stride_bytes=output_stride_bytes;
        if(output_stride_bytes==0) state.dispatch_cache_valid=false;
        draw(6,vertex_count,local_vertices,world_vertices,state.matrix_source,
             state.position_source,state.output_stride_bytes);
    } catch(...) {
        set_matrix(old_matrix);
        set_position(old_position);
        state.output_stride_bytes=old_stride;
        if(old_stride==0) state.dispatch_cache_valid=false;
        throw;
    }
    set_matrix(old_matrix);
    set_position(old_position);
    state.output_stride_bytes=old_stride;
    if(old_stride==0) state.dispatch_cache_valid=false;
}
}
