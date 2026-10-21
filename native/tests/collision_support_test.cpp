#include "mco/collision_support.hpp"
#include <array>
#include <stdexcept>

int main() {
    std::array<std::byte,65536> grid{};
    std::array<std::byte,4096> nodes{};
    const mco::SpatialQueryMemory memory{grid,nodes,0x71000000};
    const mco::TrackSurfaceWorld world{memory,{0,0},{1,1},0x71000400,
                                       0x71000800,0,0};
    std::array<float,66> local{};
    for(std::size_t i=0;i<22;++i) local[i*3+1]=2.f;
    const std::array<float,9> identity{1,0,0,0,1,0,0,0,1};
    const std::array<float,3> position{3,4,5};
    const std::array<std::byte,68> seed{};
    const auto geometry=mco::correct_support_geometry(world,position,identity,local,seed,0.f);
    if(geometry.position!=position || geometry.correction!=std::array<float,3>{0,0,0})
        throw std::runtime_error("upper support points changed object position");
    for(const auto& query:geometry.queries)
        if(query.has_surface || query.eligible)
            throw std::runtime_error("upper support point incorrectly queried terrain");

    mco::CollisionImpactBody body{};
    body.position=position;
    body.mass=1.f;
    const std::array<std::array<float,2>,32> coefficients{};
    const auto result=mco::resolve_support_contacts(world,body,geometry,coefficients,1.f,0);
    if(result.support_count!=0 || result.body.position!=position)
        throw std::runtime_error("empty support pass changed the body");
}
