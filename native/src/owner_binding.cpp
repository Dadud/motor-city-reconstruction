#include "mco/owner_binding.hpp"
#include <bit>
#include <cmath>
#include <cstdint>
#include <stdexcept>
namespace mco {
namespace {
void finite(float value) {if(!std::isfinite(value)) throw std::invalid_argument("finite owner observations required");}
std::uint32_t word(std::span<const std::byte> image,unsigned offset) {
    std::uint32_t result=0;for(unsigned k=0;k<4;++k) result|=std::to_integer<std::uint32_t>(image[offset+k])<<(k*8);return result;
}
}
std::array<float,3> body_inertia_scales(int shape,std::array<float,3> initial) {
    std::array<std::uint32_t,3> bits;
    switch(shape) {
    case 6:bits={0x3f266666,0x3f2e147b,0x3f4ccccd};break;
    case 0:case 2:bits={0x3f6147ae,0x3f70a3d7,0x3f547ae1};break;
    case 1:case 7:case 3:bits={0x3f19999a,0x3f4ccccd,0x3f333333};break;
    case 4:case 5:bits={0x3f266666,0x3f3ae148,0x3f59999a};break;
    default:for(auto value:initial) finite(value);return initial;
    }
    return {std::bit_cast<float>(bits[0]),std::bit_cast<float>(bits[1]),std::bit_cast<float>(bits[2])};
}
OwnerInertia bind_owner_inertia(float input_mass,std::array<float,3> extents,int shape) {
    finite(input_mass);if(input_mass<0) throw std::invalid_argument("nonnegative mass required");
    for(auto value:extents) {finite(value);if(value<=0) throw std::invalid_argument("positive half extents required");}
    OwnerInertia result{};result.mass=input_mass==0?1000.f:input_mass;
    result.inverse_mass=static_cast<float>(1./result.mass);result.half_extents=extents;result.shape_scales=body_inertia_scales(shape);
    const double x=static_cast<double>(extents[0])*extents[0]*4.;
    const double y=static_cast<double>(extents[1])*extents[1]*4.;
    const double z=static_cast<double>(extents[2])*extents[2]*4.;
    const std::array<double,3> sums{z+y,z+x,y+x};
    for(unsigned i=0;i<3;++i) {
        result.inertia[i]=static_cast<float>(sums[i]*result.shape_scales[i]*result.mass*std::bit_cast<float>(0x3daaaaabu));
        result.inverse_inertia[i]=static_cast<float>(1./result.inertia[i]);finite(result.inertia[i]);finite(result.inverse_inertia[i]);
    }
    return result;
}
AxleLevers bind_axle_levers(float wheelbase,float fraction) {
    finite(wheelbase);finite(fraction);if(wheelbase<=0) throw std::invalid_argument("positive wheelbase required");
    return {static_cast<float>((1.-fraction)*wheelbase),static_cast<float>(static_cast<double>(wheelbase)*fraction)};
}
StartupCOMCoordinates bind_startup_com(float height,float half,float marker,float lever) {
    finite(height);finite(half);finite(marker);finite(lever);
    return {static_cast<float>(static_cast<double>(height)*std::bit_cast<float>(0x3f68ba2eu)-half),static_cast<float>(static_cast<double>(marker)-lever)};
}
FinalizedOwnerBinding bind_finalized_owner(std::span<const std::byte> config,std::array<float,3> extents,bool finalized) {
    if(!finalized || config.size()!=0x820) throw std::invalid_argument("finalized configuration image required");
    auto n=[&](unsigned offset){return std::bit_cast<float>(word(config,offset));};
    return {bind_owner_inertia(n(0x20),extents,std::bit_cast<std::int32_t>(word(config,0x48))),bind_axle_levers(n(0x2c),n(0x3c))};
}
}
