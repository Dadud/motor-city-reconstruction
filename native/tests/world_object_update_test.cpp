#include "mco/world_object_update.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

int main() {
    mco::WorldObjectUpdate value{};
    value.object_id=1; value.active=true;
    value.position={2,-3,1}; value.linear_velocity={0.75f,-0.25f,0.5f};
    value.angular_velocity={0.03125f,-0.015625f,0.0078125f};
    value.center_of_mass={0.25f,-0.5f,0.125f};
    value.rotation={1,0,0,0,1,0,0,0,1};
    value.projection_vector={0.5f,-0.25f,1};
    for(std::size_t i=0;i<22;++i) {
        value.local_vertices[i*3]=static_cast<float>(i);
        value.local_vertices[i*3+1]=static_cast<float>(i+1);
        value.local_vertices[i*3+2]=static_cast<float>(i+2);
    }
    auto result=mco::update_world_object(value,0);
    assert(result.position!=value.position);
    assert(result.rotation!=value.rotation);
    assert(result.transposed_rotation[1]==result.rotation[3]);
    const auto expected_x=(((result.local_vertices[0]*result.rotation[0])+
                            result.local_vertices[1]*result.rotation[3])+
                            result.local_vertices[2]*result.rotation[6])+result.position[0];
    assert(result.world_vertices[0]==expected_x);
    assert(result.projected[0]==result.rotation[0]*0.5f+
                                result.rotation[1]*-0.25f+result.rotation[2]);
    value.active=false;
    result=mco::update_world_object(value,0);
    assert(result.position==value.position);
    value.active=true;
    result=mco::update_world_object(value,2);
    assert(result.rotation.size()==9);
}
