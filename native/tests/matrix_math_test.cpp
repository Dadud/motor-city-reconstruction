#include "mco/matrix_math.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cmath>

int main() {
    const std::array<std::uint32_t,9> values{0x7fc12345,0x80000000,0,0x3f800000,
        0xbf800000,0x7f800000,0xff800000,1,0xffffffff};
    const auto out=mco::transpose_3x3_words(values);
    assert((out==std::array<std::uint32_t,9>{values[0],values[3],values[6],
        values[1],values[4],values[7],values[2],values[5],values[8]}));
    assert(mco::dot_3_f32({1,2,3},{4,-5,6})==12.0f);
    assert(mco::dot_3_f32({1e20f,1,-1e20f},{1,1,1})==0.0f);
    const auto identity=std::array<float,9>{1,0,0,0,1,0,0,0,1};
    assert(mco::integrate_rotation_matrix(identity,{0,0,0})==identity);
    const auto rotated=mco::integrate_rotation_matrix(identity,{0.25f,0,0});
    assert(std::fabs(rotated[4])<1e-6f && std::fabs(rotated[5]-1.0f)<1e-6f);
    assert(mco::repair_rotation_matrix(identity)==identity);
    const auto corrected=mco::repair_rotation_matrix({1.01f,0.01f,0,-0.01f,0.99f,
                                                       0.02f,0,-0.02f,1.02f});
    assert(std::fabs(corrected[0]*corrected[0]+corrected[3]*corrected[3]+
                     corrected[6]*corrected[6]-1.0f)<1e-5f);
}
