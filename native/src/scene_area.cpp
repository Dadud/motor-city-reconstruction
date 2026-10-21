#include "mco/scene_area.hpp"
#include "mco/raster_bounds.hpp"
#include "mco/raster_fill.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace mco {
// ABI from the sole call site: 0x53a7c8 pushes [EBP+0xc], then
// 0x53a7c9 pushes EDI (the owner); the callee reads its first argument at
// [EBP+8] and ends in plain RET. The ADD ESP,0x14 at 0x53a805 is outside
// this call's argument cleanup and does not describe its arity.
// The return is binary32 in ST0: 0x53a7ff FCOM compares it against 0x0.
// Ghidra's pseudocode and direct assembly agree on the two-argument call.
// Arg1 is a pointer, not a number: 0x483487 loads [EBP+8] into EAX and
// 0x48348a dereferences it at +0x490. The FIMUL [EBP+8] on the last block
// belongs to a different path, and that slot is overwritten with ECX at
// 0x4836c4 before the divide, so it reads a reused scratch value.
// Body characterization: the routine asks 0x006ee510 for a 0x12e32-byte
// raster buffer tagged by the string at 0x890238, zeroes that buffer, then walks
// per-surface geometry indexed by a 16-bit surface id (model+0x420,
// +0x620, +0x720, triangle data at +0x48 and +0x2038), accumulating
// surface area. Resource/node ownership and the real allocator remain open.

float scene_area_from_geometry(std::span<const RasterMesh> meshes, bool raster_enabled) {
    if(!raster_enabled) return 0.0f;
    float min_x=1'000'000.0f, min_y=1'000'000.0f;
    float max_x=-1'000'000.0f, max_y=-1'000'000.0f;
    bool has_triangle=false;
    for(const auto& mesh:meshes) {
        if(!mesh.has_model || mesh.mesh_type>=16) continue;
        for(const auto value:mesh.position)
            if(!std::isfinite(value))
                throw std::invalid_argument("finite surface position required");
        const bool mirror=mesh.mesh_type==5 || mesh.mesh_type==6 ||
                          mesh.mesh_type==9 || mesh.mesh_type==10 ||
                          mesh.mesh_type==13;
        for(const auto& face:mesh.faces) {
            has_triangle=true;
            for(const auto index:face) {
                if(mesh.vertex_base>mesh.vertices.size() ||
                   index>=mesh.vertices.size()-mesh.vertex_base)
                    throw std::invalid_argument("face index outside mesh vertex range");
                const auto& vertex=mesh.vertices[mesh.vertex_base+index];
                if(!std::isfinite(vertex[0]) || !std::isfinite(vertex[1]))
                    throw std::invalid_argument("finite mesh vertex required");
                const float x=static_cast<float>((mirror ? -static_cast<double>(vertex[0])
                                                          : static_cast<double>(vertex[0]))+
                                                 mesh.position[0]);
                const float y=static_cast<float>(static_cast<double>(vertex[1])+mesh.position[1]);
                min_x=std::min(min_x,x);
                max_x=std::max(max_x,x);
                min_y=std::min(min_y,y);
                max_y=std::max(max_y,y);
            }
        }
    }
    if(!has_triangle || min_x==max_x || min_y==max_y)
        return 0.0f;
    const auto bitmap=rasterize_scene_geometry(meshes,min_x,max_x,min_y,max_y);
    const auto occupied=occupied_raster_bounds(bitmap);
    if(occupied.count==0) return 0.0f;
    const auto pixel_width=occupied.max_x+1-occupied.min_x;
    const auto pixel_height=occupied.max_y+1-occupied.min_y;
    if(pixel_width==0 || pixel_height==0) return 0.0f;
    const double numerator=(static_cast<double>(max_y)-min_y)*0.5*
                           (static_cast<double>(max_x)-min_x)*0.5*4.0*occupied.count;
    return static_cast<float>(numerator/(pixel_width*pixel_height));
}

float scene_area_from_nodes(std::span<const RasterSceneNode> nodes,
                            bool raster_enabled) {
    const auto meshes=raster_meshes_from_nodes(nodes);
    return scene_area_from_geometry(meshes,raster_enabled);
}

float scene_area(std::uint32_t, std::uint32_t) {
    throw std::logic_error(
        "cell scene_area scaffolded: implement original 0x483450");
}

}  // namespace mco
