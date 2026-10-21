#include "mco/geometry_transform.hpp"
#include <stdexcept>

namespace mco {
std::array<float,66> transform_world_vertices_22(
    const std::array<float,66>& input,
    const std::array<float,9>& matrix,
    const std::array<float,3>& position) noexcept {
    std::array<float,66> output{};
    for(std::size_t i=0;i<22;++i) {
        const auto offset=i*3;
        const auto x=input[offset], y=input[offset+1], z=input[offset+2];
        const auto x0=x*matrix[0],x1=x0+y*matrix[3],x2=x1+z*matrix[6];
        const auto y0=x*matrix[1],y1=y0+y*matrix[4],y2=y1+z*matrix[7];
        const auto z0=x*matrix[2],z1=z0+y*matrix[5],z2=z1+z*matrix[8];
        output[offset]=x2+position[0];
        output[offset+1]=y2+position[1];
        output[offset+2]=z2+position[2];
    }
    return output;
}

void add_vector_to_points(const float* source,
                          const std::array<float,3>& translation,
                          float* destination,
                          std::size_t count) {
    if (count != 0 && (source == nullptr || destination == nullptr))
        throw std::invalid_argument("nonempty point translation requires valid buffers");
    for (std::size_t i = 0; i < count; ++i) {
        const auto offset = i * 3;
        const float x = source[offset], y = source[offset + 1], z = source[offset + 2];
        destination[offset] = x + translation[0];
        destination[offset + 1] = y + translation[1];
        destination[offset + 2] = z + translation[2];
    }
}
}
