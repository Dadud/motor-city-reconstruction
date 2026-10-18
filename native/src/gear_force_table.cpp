#include "mco/gear_force_table.hpp"
#include "mco/engine_update.hpp"
#include <algorithm>
#include <bit>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <vector>
namespace mco {
namespace {
float store(double value) {
    if(!std::isfinite(value)||std::abs(value)>std::numeric_limits<float>::max())
        throw std::invalid_argument("finite binary32 gear-force value required");
    return static_cast<float>(value);
}
int nearest(float value) {
    const double low=std::floor(double(value)),fraction=double(value)-low;
    return static_cast<int>(low+(fraction>.5||(fraction==.5&&std::fmod(low,2.)!=0)));
}
}
std::array<float,135> gear_force_table(std::span<const std::byte> c,
        const std::array<float,8>& steps,unsigned selector) {
    if(c.size()!=0x820||selector>=8) throw std::invalid_argument("complete configuration and selector in [0,7] required");
    auto word=[&](unsigned offset) {std::uint32_t v=0;for(unsigned k=0;k<4;++k)
        v|=std::uint32_t(std::to_integer<unsigned char>(c[offset+k]))<<(k*8);return v;};
    auto get=[&](unsigned offset) {return store(std::bit_cast<float>(word(offset)));};
    for(float v:steps)store(v);
    const auto idle=std::bit_cast<std::int32_t>(word(0x6c)),maximum=std::bit_cast<std::int32_t>(word(0x70));
    if(idle<0||idle>maximum||maximum>12000) throw std::invalid_argument("ordered RPM bounds in [0,12000] required");
    std::vector<float> curve;for(unsigned i=0;i<26;++i)curve.push_back(get(0x80+i*4));
    const float radius=store(((double(get(0x228))*double(.001f))*(double(get(0x22c))*double(.01f))*2+
        double(get(0x230))*double(.0254f))*.5);
    if(radius<=0)throw std::invalid_argument("positive rear tire radius required");
    const float gear=get(0x334+selector*4),final=get(0x374);
    const float multiplier=store(double(get(0x354+selector*4))*double(gear)*double(final));
    const double ratio=double(gear)*double(final);
    const float correction=std::clamp(store(ratio*double(.0025f)*ratio+1.),1.f,1.5f);
    std::array<float,135> result{};
    for(unsigned i=0;i<result.size();++i) {
        const float rpm=std::clamp(store(double(i)*steps[selector]),0.f,12000.f);
        if(rpm<idle||rpm>maximum)continue;
        const float force=store(curve_torque_at_rpm(curve,nearest(rpm))*double(multiplier));
        result[i]=store(double(force)/(double(correction)*double(radius)));
    }
    return result;
}
}
