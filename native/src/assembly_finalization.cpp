#include "mco/assembly_finalization.hpp"
#include "mco/assembly_weight.hpp"
#include <algorithm>
#include <bit>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
namespace mco {
std::array<std::byte,0x820> finalize_loaded_configuration(
    std::span<const std::byte> configuration,bool components_loaded) {
    if(!components_loaded) throw std::invalid_argument("complete component loading and quality updates first");
    if(configuration.size()!=0x820) throw std::invalid_argument("expected 0x820-byte mechanical configuration");
    std::array<std::byte,0x820> out;
    std::copy(configuration.begin(),configuration.end(),out.begin());
    auto word=[&](std::size_t offset) {
        std::uint32_t v=0;
        for(unsigned i=0;i<4;++i) v|=std::to_integer<std::uint32_t>(out[offset+i])<<(i*8);
        return v;
    };
    auto number=[&](std::size_t offset) -> double {
        const auto v=std::bit_cast<float>(word(offset));
        if(!std::isfinite(v)) throw std::invalid_argument("finite postload observation required");
        return v;
    };
    auto put=[&](std::size_t offset,double v) {
        if(!std::isfinite(v) || std::abs(v)>std::numeric_limits<float>::max())
            throw std::invalid_argument("finite postload result required");
        const auto bits=std::bit_cast<std::uint32_t>(static_cast<float>(v));
        for(unsigned i=0;i<4;++i) out[offset+i]=static_cast<std::byte>((bits>>(8*i))&255);
    };
    constexpr std::array<float,10> coefficients{.45f,.42f,.9f,.9f,.47f,.46f,.45f,.52f,1.02f,1.7f};
    auto coefficient=[&](std::size_t offset) -> double {
        const auto selector=word(offset);
        if(selector>=10) throw std::invalid_argument("postload coefficient selector outside [0,9]");
        return coefficients[selector];
    };
    if(number(0x5a0)<=0) {
        const auto selector=word(0x57c);
        put(0x5b0,selector==0 ? .025f : selector==1 ? .03f : 0.f);
    }
    if(number(0x610)!=0 && number(0x620)!=0) {
        std::copy_n(out.begin()+0x610,4,out.begin()+0x114);
        std::copy_n(out.begin()+0x620,4,out.begin()+0x118);
    }
    put(0x28,number(0x20)*static_cast<double>(.02f)+number(0x28));
    constexpr std::array<std::size_t,7> selectors{0x444,0x514,0x3b0,0x538,0x480,0x4b0,0x498};
    constexpr std::array<std::size_t,7> masses{0x428,0x504,0x3a4,0x52c,0x478,0x4ac,0x490};
    double total=coefficient(selectors[0])*number(masses[0]);
    for(std::size_t i=1;i<selectors.size();++i) total+=coefficient(selectors[i])*number(masses[i]);
    total+=number(0x55c)*static_cast<double>(.42f);
    total+=coefficient(0x580)*number(0x574);
    total+=(number(0x4f0)*static_cast<double>(.4f))*static_cast<double>(1.92f);
    if(total==0) throw std::invalid_argument("nonzero postload weighted divisor required");
    put(0x448,1./total);
    AssemblyWeightInputs weight{number(0x1c),number(0x40),number(0x2c),number(0x680),{}, {}};
    constexpr std::array<std::size_t,23> front{0x428,0x504,0x52c,0x490,0x5c8,0x628,0x608,
        0x700,0x220,0x648,0x660,0x3d8,0x378,0x3ec,0x3a4,0x3c0,0x408,0x55c,0x574,0x4d4,0x4c0,0x4f0,0x80c};
    constexpr std::array<std::size_t,13> rear{0x6d8,0x5e8,0x638,0x618,0x70c,0x324,0x654,
        0x670,0x418,0x7bc,0x58c,0x5a0,0x5b4};
    for(std::size_t i=0;i<front.size();++i) weight.front_masses[i]=number(front[i]);
    for(std::size_t i=0;i<rear.size();++i) weight.rear_masses[i]=number(rear[i]);
    put(0x3c,assembled_front_weight_fraction(weight));
    return out;
}
}
