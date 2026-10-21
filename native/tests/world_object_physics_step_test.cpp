#include "mco/world_object_physics_step.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <array>
#include <cassert>
#include <cstring>
#include <stdexcept>

int main() {
    std::array<std::uint8_t,mco::world_object_record_size> bytes{};
    const auto put=[&](std::size_t offset,float value){std::memcpy(bytes.data()+offset,&value,4);};
    const auto get=[&](std::size_t offset){float value{};std::memcpy(&value,bytes.data()+offset,4);return value;};
    int environment_calls=0, force_calls=0;
    const mco::WorldObjectPhysicsChild environment=[&](auto){++environment_calls;};
    const mco::WorldObjectPhysicsChild force=[&](auto){++force_calls;};
    bytes[4]=1;
    put(0x14,1.25f);put(0x18,-2.5f);put(0x1c,0.75f);
    put(0x38,0.125f);put(0x3c,-0.25f);put(0x40,0.5f);
    put(0x31c,0.75f);put(0x320,0.125f);put(0x324,-0.25f);
    put(0x328,0.5f);put(0x32c,1.0f);put(0x330,0.25f);
    put(0x334,-0.125f);put(0x338,0.375f);put(0x33c,0.875f);
    put(0x50,4.0f);put(0x2f0,2.0f);put(0x2f4,0.75f);put(0x2f8,1.5f);
    mco::step_world_object_physics(bytes,false,0,environment,force);
    assert(environment_calls==1 && force_calls==1);
    assert(get(0x2c)!=0.0f && get(0x14)!=1.25f && get(0x3c0)>0.0f);

    bytes[6]=1;
    const std::array<std::uint8_t,12> before_velocity{
        bytes[0x14],bytes[0x15],bytes[0x16],bytes[0x17],bytes[0x18],bytes[0x19],
        bytes[0x1a],bytes[0x1b],bytes[0x1c],bytes[0x1d],bytes[0x1e],bytes[0x1f]};
    mco::step_world_object_physics(bytes,true,1,environment,force);
    assert(environment_calls==2 && force_calls==1);
    for (std::size_t i=0;i<before_velocity.size();++i)
        assert(bytes[0x14+i]==before_velocity[i]);
    assert(get(0x3c0)>0.0f);

    bool rejected=false;
    try { mco::step_world_object_physics(bytes,false,0,{},force); }
    catch(const std::invalid_argument&) { rejected=true; }
    assert(rejected);
}
