#include "mco/world_object_maintenance.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <stdexcept>

int main() {
    using namespace mco;
    const auto identity=[](WorldObjectMotion value){return value;};
    WorldObjectMaintenance state{{0,{4,5,6},{1,2,3}},true,0,1};
    const auto damped=maintain_world_object(state,identity);
    assert(damped.motion.linear_velocity[0]==4.0f*0.99f && damped.motion.angular_velocity[2]==3.0f*0.99f);
    state={{0,{0,0,0},{12,0,0}},true,1,1};
    const auto capped=maintain_world_object(state,identity);
    assert(capped.motion.angular_velocity[0]==10.0f);
    state={{33,{0,0,0},{0,0,0}},true,0,0};
    const auto nudged=maintain_world_object(state,identity);
    assert(nudged.motion.angular_velocity[0]==0.01f);
    state.active=false;
    const auto skipped=maintain_world_object(state,[](auto){assert(false);return WorldObjectMotion{};});
    assert(!skipped.active);
    bool rejected=false;
    try { (void)maintain_world_object(state,{}); } catch(const std::invalid_argument&) { rejected=true; }
    assert(rejected);
}
