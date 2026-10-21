#include "mco/scene_area.hpp"
#include <bit>
#include <cstdint>
#include <iostream>
#include <sstream>
#include <string>

int main() {
    std::string line;
    while(std::getline(std::cin,line)) {
        if(line.empty()) continue;
        std::istringstream input(line);
        input>>std::hex;
        std::uint32_t count{},bounds[4]{};
        if(!(input>>count>>bounds[0]>>bounds[1]>>bounds[2]>>bounds[3])) return 2;
        if(count>256) return 3;
        std::vector<mco::FceModel> models;
        std::vector<mco::RasterSceneNode> nodes;
        models.reserve(count);
        nodes.reserve(count);
        for(std::uint32_t m=0;m<count;++m) {
            std::uint32_t available{},type{},surface{},vertex_base{},face_base{};
            std::uint32_t vertices{},faces{},position[3]{};
            if(!(input>>available>>type>>surface>>vertex_base>>face_base>>vertices>>faces>>
                 position[0]>>position[1]>>position[2])) return 4;
            if(vertices>4096 || faces>4096) return 5;
            mco::RasterMesh mesh;
            mesh.has_model=available!=0;
            mesh.mesh_type=std::bit_cast<std::int32_t>(type);
            mesh.surface_id=static_cast<std::int16_t>(surface);
            mesh.vertex_base=vertex_base;
            mesh.face_base=face_base;
            for(std::size_t i=0;i<3;++i) mesh.position[i]=std::bit_cast<float>(position[i]);
            mesh.vertices.resize(vertices);
            for(auto& vertex:mesh.vertices) for(auto& coordinate:vertex) {
                std::uint32_t word{};
                if(!(input>>word)) return 6;
                coordinate=std::bit_cast<float>(word);
            }
            mesh.faces.resize(faces);
            for(auto& face:mesh.faces) for(auto& index:face) {
                std::uint32_t word{};
                if(!(input>>word)) return 7;
                index=word;
            }
            if(!mesh.has_model || mesh.mesh_type>=16) {
                nodes.push_back({nullptr,mesh.surface_id,mesh.mesh_type});
                continue;
            }
            if(mesh.surface_id<0 || mesh.surface_id>=64 ||
               mesh.vertex_base>mesh.vertices.size()) return 8;
            mco::FceModel model{};
            model.version=0x101014;
            model.parts.resize(static_cast<std::size_t>(mesh.surface_id)+1);
            auto& part=model.parts[static_cast<std::size_t>(mesh.surface_id)];
            part.origin=mesh.position;
            part.vertices.assign(mesh.vertices.begin()+mesh.vertex_base,
                                 mesh.vertices.end());
            for(const auto& indices:mesh.faces) {
                mco::FceTriangle face{};
                for(std::size_t i=0;i<3;++i) {
                    if(indices[i]>UINT32_MAX) return 9;
                    face.indices[i]=static_cast<std::uint32_t>(indices[i]);
                }
                part.triangles.push_back(face);
            }
            models.push_back(std::move(model));
            nodes.push_back({&models.back(),mesh.surface_id,mesh.mesh_type});
        }
        const float value=mco::scene_area_from_nodes(nodes);
        std::cout<<std::hex<<std::bit_cast<std::uint32_t>(value)<<'\n';
    }
}
