#include "mco/scene_area.hpp"
#include <cassert>
#include <array>
#include <cstdint>
int main() {
    const mco::RasterMesh triangle{
        {{{1,1,0}},{{9,1,0}},{{5,9,0}}}, {{{0,1,2}}}, {0,0,0}, 0, true};
    const std::array meshes{triangle};
    const float value=mco::scene_area_from_geometry(meshes);
    assert(value>31.96f && value<31.98f);
    assert(mco::scene_area_from_geometry(meshes,false)==0.0f);
    const mco::RasterMesh malformed{{{{0,0,0}}},{{{0,1,0}}},{0,0,0},0,true};
    const std::array bad_meshes{malformed};
    assert(mco::scene_area_from_geometry(bad_meshes,false)==0.0f);

    mco::FcePart part{};
    part.origin={1,1,0};
    part.vertices={{{0,0,0}},{{8,0,0}},{{4,8,0}}};
    mco::FceTriangle face{};
    face.indices={0,1,2};
    part.triangles.push_back(face);
    mco::FceModel model{};
    model.parts.push_back(part);
    const std::array nodes{mco::RasterSceneNode{&model,0,0}};
    assert(mco::scene_area_from_nodes(nodes)==value);
}
