#include "mco/contact_force.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <array>
#include <cassert>
#include <cstring>
#include <stdexcept>

int main() {
    std::array<std::uint8_t,0x4f8> record{};
    const auto put=[&](std::size_t offset,float value){std::memcpy(record.data()+offset,&value,4);};
    put(0x54,1.0f);
    const std::array<float,9> identity{1,0,0,0,1,0,0,0,1};
    std::memcpy(record.data()+0x78,identity.data(),36);
    std::memcpy(record.data()+0x9c,identity.data(),36);
    put(0x2fc,1);put(0x300,1);put(0x304,1);
    const auto response=mco::contact_response(record,{-2,0,0},{1,2,0},{1,0,0});
    assert(response.linear[0]==-2.0f && response.linear[1]==0.0f && response.linear[2]==0.0f);
    assert(response.angular[2]==4.0f);

    record[4]=1;
    put(0x14,1);put(0x18,0);put(0x1c,0);
    std::int16_t count=1;std::memcpy(record.data()+0x3bc,&count,2);
    for(const auto offset:{0x248u,0x254u,0x260u,0x26cu,0x278u,0x284u}) {
        put(offset,1);put(offset+4,0);put(offset+8,0);
    }
    int calls=0;
    mco::contact_forces_step(record,[&](auto,const auto&,const auto&,const auto&){
        ++calls;return mco::ContactResponse{{1,0,0},{0,1,0}};
    });
    assert(calls==6);

    bool rejected=false;
    try { mco::contact_forces_step(record,{}); }
    catch(const std::invalid_argument&) { rejected=true; }
    assert(rejected);
}
