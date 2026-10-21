#include "mco/raster_scene.hpp"
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
        std::vector<mco::RasterMesh> meshes;
        meshes.reserve(count);
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
            meshes.push_back(std::move(mesh));
        }
        const auto mask=mco::rasterize_scene_geometry(
            meshes,std::bit_cast<float>(bounds[0]),std::bit_cast<float>(bounds[1]),
            std::bit_cast<float>(bounds[2]),std::bit_cast<float>(bounds[3]));
        static constexpr char digits[]="0123456789abcdef";
        for(const auto value:mask) std::cout<<digits[value>>4]<<digits[value&15];
        std::cout<<'\n';
    }
}
