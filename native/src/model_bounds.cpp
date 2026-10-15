#include "mco/model_bounds.hpp"
#include <cmath>
#include <stdexcept>
namespace mco {
std::optional<PartBounds> transformed_part_bounds(const FcePart& part, bool mirrored) {
    if(part.vertices.size()>1000000) throw std::invalid_argument("bounded part geometry required");
    for(float value:part.origin)
        if(!std::isfinite(value)) throw std::invalid_argument("finite part origin required");
    std::optional<PartBounds> result;
    for(const auto& point:part.vertices) {
        Vec3 position{};
        for(unsigned axis=0;axis<3;++axis) {
            if(!std::isfinite(point[axis])) throw std::invalid_argument("finite vertex required");
            const float local=axis==0 && mirrored ? -point[axis] : point[axis];
            position[axis]=local+part.origin[axis];
        }
        if(!result) result=PartBounds{position,position};
        else for(unsigned axis=0;axis<3;++axis) {
            if(position[axis]<=result->minimum[axis]) result->minimum[axis]=position[axis];
            if(position[axis]>=result->maximum[axis]) result->maximum[axis]=position[axis];
        }
    }
    return result;
}
}
