#include "mco/path_side.hpp"
#include <stdexcept>
#include <cmath>

namespace mco {

// Decompiled pseudocode of 0x42ee50, kept as the implementation draft.
// The oracle against the original, not this text, decides correctness.


std::uint32_t path_side(std::span<const std::array<float,3>> points, std::span<const float,3> position, std::uint32_t index) {
    if(index>=points.size() || points.size()>0x7fffffffu)
        throw std::invalid_argument("path index outside supplied points");
    auto next=index+1;
    if(next>=points.size()) next=0;
    for(auto value:position) if(!std::isfinite(value) || std::abs(value)>1e20f)
        throw std::invalid_argument("unsupported path query coordinate");
    for(auto i:{index,next}) for(auto value:points[i])
        if(!std::isfinite(value) || std::abs(value)>1e20f)
            throw std::invalid_argument("unsupported path point coordinate");
    const double x=points[next][0],z=points[next][2];
    const double left=(static_cast<double>(points[index][2])-z)*(static_cast<double>(position[0])-x);
    const double right=(static_cast<double>(points[index][0])-x)*(static_cast<double>(position[2])-z);
    return left<right ? 8u : 2u;
}

}  // namespace mco
