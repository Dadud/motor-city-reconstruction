#include "mco/spatial_grid_lookup.hpp"
#include <stdexcept>
#include <cmath>
#include <cfenv>
#include <limits>

namespace mco {

// Decompiled pseudocode of 0x552880, kept as the implementation draft.
// The oracle against the original, not this text, decides correctness.


std::uint32_t spatial_grid_lookup(const SpatialQueryMemory &memory, std::span<const float,3> position, std::span<const float,2> origin, std::span<const float,2> scale) {
    if(std::fegetround()!=FE_TONEAREST)
        throw std::invalid_argument("spatial query requires nearest-even rounding");
    auto coordinate=[](float value,float minimum,float factor) {
        const float stored=static_cast<float>((static_cast<double>(value)-minimum)*factor);
        if(!std::isfinite(stored)) return std::numeric_limits<std::int32_t>::min();
        const double rounded=std::nearbyint(static_cast<double>(stored));
        if(rounded < -2147483648.0 || rounded > 2147483647.0)
            return std::numeric_limits<std::int32_t>::min();
        return static_cast<std::int32_t>(rounded);
    };
    const auto x=coordinate(position[0],origin[0],scale[0]);
    const auto z=coordinate(position[2],origin[1],scale[1]);
    if(x<0 || z<0 || x>=65536 || z>=65536) return 0;
    auto node=SpatialQueryMemory::grid_address+
              (static_cast<std::uint32_t>(x)/1024*64+static_cast<std::uint32_t>(z)/1024)*16;
    if(memory.word(node)==0xdeadbeef) return node;
    for(unsigned depth=0;depth<2;++depth) {
        const unsigned bit=9-depth;
        const auto child=((static_cast<std::uint32_t>(x)>>bit)&1u)+
                         2*((static_cast<std::uint32_t>(z)>>bit)&1u);
        node=memory.word(node+child*4);
        if(node==0 || memory.word(node)==0xdeadbeef) return node;
    }
    if(!memory.diagnostic) throw std::invalid_argument("spatial diagnostic bridge required");
    memory.diagnostic(0x89900c,memory.user);
    return 0;
}

}  // namespace mco
