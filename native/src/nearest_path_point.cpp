#include "mco/nearest_path_point.hpp"
#include <stdexcept>
#include <cmath>

namespace mco {

// Decompiled pseudocode of 0x42e6b0, kept as the implementation draft.
// The oracle against the original, not this text, decides correctness.


std::uint32_t nearest_path_point(std::span<const std::array<float,3>> points, std::span<const float,3> position, std::uint32_t group, std::int32_t count) {
    const auto start=static_cast<std::uint64_t>(group)*8;
    const auto length=count>1 ? static_cast<std::uint32_t>(count) : 1u;
    if(start>=points.size() || length>points.size()-start || start+length>0x100000000ull)
        throw std::invalid_argument("path group outside supplied points");
    for(auto value:position) if(!std::isfinite(value) || std::abs(value)>1e20f)
        throw std::invalid_argument("unsupported path query coordinate");
    for(std::size_t i=start;i<start+length;++i)
        for(auto value:points[i]) if(!std::isfinite(value) || std::abs(value)>1e20f)
            throw std::invalid_argument("unsupported path point coordinate");
    auto distance=[&](std::size_t i) {
        // Original stores the Z difference as float; X remains in x87.
        const float dz=static_cast<float>(static_cast<double>(position[2])-points[i][2]);
        const double dx=static_cast<double>(position[0])-points[i][0];
        return dx*dx+static_cast<double>(dz)*dz;
    };
    auto best=static_cast<std::uint32_t>(start);
    float minimum=static_cast<float>(distance(start));
    for(std::size_t i=start+1;i<start+length;++i) {
        const double candidate=distance(i);
        // Compare unrounded candidate with stored minimum, then round on update.
        if(candidate<minimum) {best=static_cast<std::uint32_t>(i);minimum=static_cast<float>(candidate);}
    }
    return best;
}

}  // namespace mco
