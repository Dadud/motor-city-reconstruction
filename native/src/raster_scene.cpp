#include "mco/raster_scene.hpp"
#include <cmath>
#include <stdexcept>
#include <utility>

namespace mco {
std::vector<RasterMesh> raster_meshes_from_nodes(
    std::span<const RasterSceneNode> nodes) {
    std::vector<RasterMesh> meshes;
    meshes.reserve(nodes.size());
    for(const auto& node:nodes) {
        if(!node.model || node.mesh_type>=16) {
            RasterMesh skipped{};
            skipped.mesh_type=node.mesh_type;
            skipped.has_model=node.model!=nullptr;
            skipped.surface_id=node.surface_id;
            meshes.push_back(std::move(skipped));
            continue;
        }
        if(node.surface_id<0 ||
           static_cast<std::size_t>(node.surface_id)>=node.model->parts.size())
            throw std::invalid_argument("scene surface ID outside decoded FCE parts");
        const auto& part=node.model->parts[static_cast<std::size_t>(node.surface_id)];
        RasterMesh mesh{};
        mesh.vertices=part.vertices;
        mesh.faces.reserve(part.triangles.size());
        for(const auto& triangle:part.triangles)
            mesh.faces.push_back({triangle.indices[0],triangle.indices[1],
                                  triangle.indices[2]});
        mesh.position=part.origin;
        mesh.mesh_type=node.mesh_type;
        mesh.surface_id=node.surface_id;
        meshes.push_back(std::move(mesh));
    }
    return meshes;
}

RasterTriangleMask rasterize_scene_geometry(
    std::span<const RasterMesh> meshes,
    float xmin, float xmax, float ymin, float ymax) {
    if(!std::isfinite(xmin) || !std::isfinite(xmax) ||
       !std::isfinite(ymin) || !std::isfinite(ymax) || xmin==xmax || ymin==ymax)
        throw std::invalid_argument("finite raster bounds with nonzero extents required");
    RasterTriangleMask bitmap{};
    for(const auto& mesh:meshes) {
        if(!mesh.has_model || mesh.mesh_type>=16) continue;
        for(const auto& value:mesh.position)
            if(!std::isfinite(value))
                throw std::invalid_argument("finite surface position required");
        for(const auto& vertex:mesh.vertices)
            for(const auto value:vertex)
                if(!std::isfinite(value))
                    throw std::invalid_argument("finite mesh vertex required");
        const bool mirror=mesh.mesh_type==5 || mesh.mesh_type==6 ||
                          mesh.mesh_type==9 || mesh.mesh_type==10 ||
                          mesh.mesh_type==13;
        for(const auto& face:mesh.faces) {
            RasterTriangle triangle{};
            for(std::size_t i=0;i<3;++i) {
                if(mesh.vertex_base>mesh.vertices.size() ||
                   face[i]>=mesh.vertices.size()-mesh.vertex_base)
                    throw std::invalid_argument("face index outside mesh vertex range");
                const auto& vertex=mesh.vertices[mesh.vertex_base+face[i]];
                const double x=mirror ? -static_cast<double>(vertex[0]) : vertex[0];
                triangle[i][0]=static_cast<float>(x+mesh.position[0]);
                triangle[i][1]=static_cast<float>(static_cast<double>(vertex[1])+mesh.position[1]);
            }
            const auto face_mask=rasterize_projected_triangle(
                triangle,xmin,xmax,ymin,ymax);
            for(std::size_t i=0;i<bitmap.size();++i)
                if(face_mask[i]) bitmap[i]=1;
        }
    }
    return bitmap;
}
}
