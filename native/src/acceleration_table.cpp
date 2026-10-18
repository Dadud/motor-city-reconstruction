#include "mco/acceleration_table.hpp"
#include "mco/engine_update.hpp"
#include <algorithm>
#include <bit>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <vector>
namespace mco {
namespace {
float store(double v){if(!std::isfinite(v)||std::abs(v)>std::numeric_limits<float>::max())throw std::invalid_argument("finite acceleration value required");return static_cast<float>(v);}
std::uint32_t word(std::span<const std::byte> c,unsigned offset){std::uint32_t v=0;for(unsigned k=0;k<4;++k)v|=std::uint32_t(std::to_integer<unsigned char>(c[offset+k]))<<(k*8);return v;}
float get(std::span<const std::byte> c,unsigned offset){return store(std::bit_cast<float>(word(c,offset)));}
std::int32_t integer(std::span<const std::byte> c,unsigned offset){return std::bit_cast<std::int32_t>(word(c,offset));}
void validate(std::span<const std::byte> c,std::span<const std::byte> r){
    if(c.size()!=0x820||r.size()!=0x4a8)throw std::invalid_argument("complete startup records required");
    if(integer(c,0x70)<=0||integer(c,0x70)>12000||get(r,0x104)<=0)throw std::invalid_argument("positive bounded maximum RPM and denominator required");
}
int nearest(float v){const double low=std::floor(double(v)),fraction=double(v)-low;return static_cast<int>(low+(fraction>.5||(fraction==.5&&std::fmod(low,2)!=0)));}
}
double startup_force(std::span<const std::byte> c,std::span<const std::byte> r,std::int32_t rpm,
        unsigned selector,float sample,bool secondary){
    validate(c,r);(void)secondary;store(sample);
    if(rpm<1||rpm>12000||selector>=8)throw std::invalid_argument("positive RPM and selector 0..7 required");
    std::vector<float> curve;for(unsigned i=0;i<26;++i)curve.push_back(get(c,0x80+i*4));
    const float torque=store(curve_torque_at_rpm(curve,rpm));
    const float fraction=store(double(rpm)/integer(c,0x70));
    const float size=store(double(integer(c,0x4d8))+1.);
    if(size<0)throw std::invalid_argument("nonnegative correction range required");
    const float angular=store(double(rpm)*double(6.2831854820251465f));
    const float deduction=store(double(size)*4.*double(fraction)*60000./double(angular));
    const float loss=std::clamp(deduction,0.f,store(double(size)*10.));
    const float remainder=store((double(torque)-double(loss))-((double(integer(c,0x4f4))+1.)*double(fraction)*2.*60000./double(angular)));
    double effective=std::max(0.f,remainder);
    if(integer(c,0x68c)!=0&&sample>=0&&sample<=10){const double t=double(sample)*double(.1f);effective=((1.-t)*t*t*t*1.5+1.)*effective;}
    const double ratio=double(get(c,0x334+selector*4))*get(c,0x374);
    const double result=((double(get(r,0x64+selector*4))*get(c,0x6e8)*effective)/(ratio*ratio*double(.0015f)+1.))/get(r,0x104);
    if(!std::isfinite(result))throw std::invalid_argument("finite startup force required");return result;
}
std::array<std::byte,0x4a8> acceleration_table(std::span<const std::byte> c,std::span<const std::byte> r){
    validate(c,r);const auto idle=integer(c,0x6c);const float mass=get(c,0x20);
    if(idle<1||idle>12000||mass<=0)throw std::invalid_argument("positive bounded idle RPM and mass required");
    const bool second=get(c,0x3e0)>0&&get(c,0x3e4)>0;
    std::array<std::byte,0x4a8> result;std::copy(r.begin(),r.end(),result.begin());unsigned index=0,selector=2;
    auto put=[&](unsigned offset,float v){const auto w=std::bit_cast<std::uint32_t>(v);for(unsigned k=0;k<4;++k)result[offset+k]=static_cast<std::byte>((w>>(k*8))&255);};
    for(unsigned sample=0;sample<112;++sample){
        if(get(r,0xac+index*4)<float(sample)){++index;++selector;}
        if(selector>=8)throw std::invalid_argument("startup shift schedule exceeds eight selectors");
        const int rpm=nearest(std::min(12000.f,std::max(store(idle),store(double(sample)*get(r,0x2c+index*4)))));
        const double force=startup_force(c,r,rpm,selector,float(sample));
        put(0x128+sample*4,force<=0?0.f:store((1./double(mass))*force));
        const double other=second?startup_force(c,r,rpm,selector,float(sample),true):force;
        put(0x2e8+sample*4,other<=0?0.f:store((1./double(mass))*other));
    }
    return result;
}
}
