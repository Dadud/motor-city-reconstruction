#include "mco/owner_wheel_setup.hpp"
#include <algorithm>
#include <bit>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
namespace mco {
namespace {
std::uint32_t word(std::span<const std::byte> bytes,std::size_t offset) {
    std::uint32_t v=0;for(unsigned k=0;k<4;++k) v|=std::to_integer<std::uint32_t>(bytes[offset+k])<<(k*8);return v;
}
double number(std::span<const std::byte> bytes,std::size_t offset) {
    const auto v=std::bit_cast<float>(word(bytes,offset));
    if(!std::isfinite(v)) throw std::invalid_argument("finite startup observations required");return v;
}
void put(StartupOwnerImage& image,std::size_t offset,double value) {
    if(!std::isfinite(value) || std::abs(value)>std::numeric_limits<float>::max()) throw std::invalid_argument("finite startup output required");
    const auto bits=std::bit_cast<std::uint32_t>(static_cast<float>(value));
    for(unsigned k=0;k<4;++k) image[offset+k]=static_cast<std::byte>((bits>>(k*8))&255);
}
std::array<double,2> stance(double front,double rear) {
    front=static_cast<float>(front+std::max(0.,static_cast<double>(static_cast<float>(front-.37f))));
    rear=static_cast<float>(rear+std::max(0.,static_cast<double>(static_cast<float>(rear-.37f))));
    return {std::min(0.,static_cast<double>(static_cast<float>(front-rear))),std::min(0.,static_cast<double>(static_cast<float>(rear-front)))};
}
StartupOwnerImage copy_owner(std::span<const std::byte> owner) {
    if(owner.size()!=0x2000) throw std::invalid_argument("expected complete owner image");
    StartupOwnerImage out;std::copy(owner.begin(),owner.end(),out.begin());return out;
}
}
StartupOwnerImage adjust_owner_stance(std::span<const std::byte> owner) {
    auto out=copy_owner(owner);auto n=[&](auto offset){return number(out,offset);};
    const auto deltas=stance(n(0x18ec),n(0x18f0));const auto front=deltas[0],rear=deltas[1],middle=(front+rear)*.5f;
    for(auto offset:{0xe4,0xf0,0x1bc}) put(out,offset,n(offset)-front);
    for(auto offset:{0xfc,0x108,0x1e0}) put(out,offset,n(offset)-rear);
    for(auto offset:{0x1c8,0x180,0x1d4}) put(out,offset,n(offset)-middle);
    for(auto offset:{0x1c0,0xe8,0xf4}) put(out,offset,n(0x18c4)+n(0x18ec));
    for(auto offset:{0x100,0x10c,0x1e4}) put(out,offset,n(0x18c8)-n(0x18f0));
    return out;
}
StartupOwnerImage initialize_owner_wheels(std::span<const std::byte> owner,std::span<const std::byte> config,bool finalized) {
    if(!finalized) throw std::invalid_argument("complete mechanical assembly first");
    if(config.size()!=0x820) throw std::invalid_argument("expected configuration image");
    auto out=copy_owner(owner);auto n=[&](auto offset){return number(out,offset);};auto c=[&](auto offset){return number(config,offset);};
    auto copy=[&](auto destination,auto source){std::copy_n(config.begin()+source,4,out.begin()+destination);};
    const std::array<double,2> radii{n(0x18ec),n(0x18f0)};
    if(std::min(radii[0],radii[1])<=0 || c(0x144)<=0) throw std::invalid_argument("positive axle radii and front template width required");
    put(out,0x6b8,radii[0]);put(out,0x7c4,radii[0]);put(out,0x8d0,radii[1]);put(out,0x9dc,radii[1]);
    const bool mass_available=word(out,0x490)!=0 && c(0x700)!=0 && c(0x70c)!=0 && c(0x220)!=0 && c(0x324)!=0;
    for(unsigned wheel=0;wheel<4;++wheel) {
        const auto base=0x6b4+wheel*0x10c;const bool front=wheel<2;
        copy(base,front?0x11c:0x120);put(out,base-0x5c,1);put(out,base-0x58,1);put(out,base+0x1c,c(0x20)*.25f);out[base+0x34]=std::byte{1};
        for(auto relative:{-0xb8,0x18,0x20,0x24,0x28,0x2c,-0x4c,-0x40,-0x3c,-0x38,-0x34,-0x30,-0x2c,-0x28}) put(out,base+relative,0);
        const double mass=mass_available ? (front?c(0x220)+c(0x700):c(0x324)+c(0x70c)) : 15.;
        const auto radius=n(base+4);const double spin=static_cast<float>(radius*radius*mass*.5f);
        if(spin<=0) throw std::invalid_argument("positive wheel inertia required");put(out,base-0x24,spin);
        const auto width=c(front?0x124:0x228)*.001f;copy(base+0x14,front?0x134:0x238);
        const auto transverse=width*width*.083333336f+spin;
        put(out,base-0x1c,transverse);put(out,base-0x20,transverse);put(out,base-0x18,1./spin);put(out,base-0x14,1./transverse);put(out,base-0x10,1./transverse);
        const double ratio=static_cast<float>(width/(c(0x144)*.001f));put(out,base+0x40,std::clamp(ratio,static_cast<double>(.9f),1.5));
    }
    const std::array<unsigned,4> flags{0x6c1,0x7cd,0x8d9,0x9e5};unsigned sum=0;
    for(unsigned k=0;k<4;++k) {out[flags[k]]=config[0x60+k];sum+=std::to_integer<unsigned>(config[0x60+k]);}
    if(sum==0) {out[0x8d9]=std::byte{1};out[0x9e5]=std::byte{1};}
    for(auto p:std::array<std::array<unsigned,2>,4>{{{0x604,0x138},{0x710,0x138},{0x928,0x23c},{0x81c,0x23c}}}) put(out,p[0],c(p[1])*.0055555557f);
    for(auto p:std::array<std::array<unsigned,2>,12>{{{0x7d4,0x134},{0x6c8,0x134},{0x8e0,0x238},{0x9ec,0x238},{0x6f8,0x140},{0x804,0x140},{0xa1c,0x244},{0x910,0x244},{0x6c4,0x130},{0x7d0,0x130},{0x9e8,0x234},{0x8dc,0x234}}}) copy(p[0],p[1]);
    const double bias=static_cast<float>(c(0x58)*.5f);put(out,0x6a8,bias);put(out,0x7b4,bias);put(out,0x9cc,.5f-bias);put(out,0x8c0,.5f-bias);
    out[0x6c0]=std::byte{1};out[0x7cc]=std::byte{1};const auto rear_drive=config[0xe4]!=std::byte{0}?std::byte{1}:std::byte{0};out[0x9e4]=rear_drive;out[0x8d8]=rear_drive;
    for(auto p:std::array<std::array<unsigned,2>,4>{{{0x6bc,0x224},{0x7c8,0x224},{0x9e0,0x328},{0x8d4,0x328}}}) {
        const auto selector=word(config,p[1]);const double limit=selector==0?160.:selector==2?240.:selector==3?300.:190.;put(out,p[0],limit*.27778f);
    }
    const auto deltas=stance(radii[0],radii[1]);const auto fx=c(0x30)*.5f,rx=c(0x34)*.5f;
    put(out,0x6fc,-fx);put(out,0x808,fx);put(out,0x914,rx);put(out,0xa20,-rx);
    for(auto offset:{0x700,0x80c}) put(out,offset,-(deltas[0]+n(0xd0)));
    for(auto offset:{0x918,0xa24}) put(out,offset,-(deltas[1]+n(0xd0)));
    for(auto offset:{0x704,0x810}) put(out,offset,n(0x18c4));
    for(auto offset:{0x91c,0xa28}) put(out,offset,n(0x18c8));
    return adjust_owner_stance(out);
}
}
