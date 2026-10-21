#include "mco/raster_scene.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

int main() {
    const mco::RasterMesh mesh{
        {{{1,1,0}},{{9,1,0}},{{5,9,0}},{{2,2,0}},{{8,2,0}},{{5,7,0}}},
        {{{0,1,2}},{{3,4,5}}}, {0,0,0}, 0, true};
    const mco::RasterMesh mirrored{
        {{{-1,1,0}},{{-9,1,0}},{{-5,9,0}}}, {{{0,1,2}}},
        {10,0,0}, 5, true};
    const mco::RasterMesh skipped{{}, {}, {0,0,0}, 16, true};
    const std::array meshes{mesh,mirrored,skipped};
    const auto mask=mco::rasterize_scene_geometry(meshes,0,10,0,10);
    std::size_t count=0;
    for(const auto value:mask) count+=value!=0;
    assert(count==24769);
}
