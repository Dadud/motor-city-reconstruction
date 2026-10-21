#include "mco/matrix_math.hpp"
#include <bit>
#include <cmath>
#include <stdexcept>

namespace mco {
namespace {
std::array<float,9> multiply(const std::array<float,9>& a,
                             const std::array<float,9>& b) noexcept {
    std::array<float,9> result{};
    for (std::size_t row=0;row<3;++row) {
        for (std::size_t col=0;col<3;++col) {
            const auto sum=static_cast<double>(a[row*3])*b[col]+
                           static_cast<double>(a[row*3+1])*b[3+col]+
                           static_cast<double>(a[row*3+2])*b[6+col];
            result[row*3+col]=static_cast<float>(sum);
        }
    }
    return result;
}
}

std::array<std::uint32_t, 9> transpose_3x3_words(
    const std::array<std::uint32_t, 9>& v) noexcept {
    return {v[0],v[3],v[6],v[1],v[4],v[7],v[2],v[5],v[8]};
}

float dot_3_f32(const std::array<float, 3>& a,
                const std::array<float, 3>& b) noexcept {
    const auto result = static_cast<double>(a[0])*b[0] +
                        static_cast<double>(a[1])*b[1] +
                        static_cast<double>(a[2])*b[2];
    return static_cast<float>(result);
}

std::array<float,9> multiply_3x3(const std::array<float,9>& a,
                                const std::array<float,9>& b) noexcept {
    std::array<float,9> result{};
    for (std::size_t i=0;i<9;++i) {
        const auto row=i/3, col=i%3;
        const std::array<std::size_t,3> order = i==0
            ? std::array<std::size_t,3>{0,2,1}
            : std::array<std::size_t,3>{0,1,2};
        const auto k0=order[0], k1=order[1], k2=order[2];
        const auto first=static_cast<double>(a[row*3+k0])*b[k0*3+col];
        const auto second=static_cast<double>(a[row*3+k1])*b[k1*3+col];
        const auto third=static_cast<double>(a[row*3+k2])*b[k2*3+col];
        result[i]=static_cast<float>(first+second+third);
    }
    return result;
}

std::array<float,9> repair_rotation_matrix(
    const std::array<float,9>& matrix, int iterations) {
    if (iterations!=10) throw std::invalid_argument("recovered repair supports ten iterations");
    const auto transposed_words=transpose_3x3_words({
        std::bit_cast<std::uint32_t>(matrix[0]),std::bit_cast<std::uint32_t>(matrix[1]),
        std::bit_cast<std::uint32_t>(matrix[2]),std::bit_cast<std::uint32_t>(matrix[3]),
        std::bit_cast<std::uint32_t>(matrix[4]),std::bit_cast<std::uint32_t>(matrix[5]),
        std::bit_cast<std::uint32_t>(matrix[6]),std::bit_cast<std::uint32_t>(matrix[7]),
        std::bit_cast<std::uint32_t>(matrix[8])});
    std::array<float,9> transposed{};
    for(std::size_t i=0;i<9;++i) transposed[i]=std::bit_cast<float>(transposed_words[i]);
    const auto gram=multiply_3x3(transposed,matrix);
    auto error=gram;
    for(const auto i : {std::size_t{0},std::size_t{4},std::size_t{8}}) error[i]-=1.0f;
    std::array<float,9> power{1,0,0,0,1,0,0,0,1};
    auto correction=power;
    constexpr std::array<float,9> coefficients{
        -0.5f,0.375f,-0.3125f,0.2734375f,-0.24609375f,
        0.2255859375f,-0.20947265625f,0.196380615234375f,
        -0.1854705810546875f};
    for(const auto coefficient:coefficients) {
        power=multiply_3x3(power,error);
        for(std::size_t i=0;i<9;++i)
            correction[i]=static_cast<float>(correction[i]+
                                              static_cast<float>(power[i]*coefficient));
    }
    return multiply_3x3(matrix,correction);
}

std::array<float,9> integrate_rotation_matrix(
    const std::array<float,9>& matrix,
    const std::array<float,3>& delta_turns) noexcept {
    constexpr float tau=6.2831854820251465f;
    std::array<std::array<float,2>,3> trig{};
    for (std::size_t i=0;i<3;++i) {
        const auto radians=static_cast<double>(delta_turns[i])*tau;
        trig[i]={static_cast<float>(std::sin(radians)),
                 static_cast<float>(std::cos(radians))};
    }
    const auto [sx,cx]=trig[0];
    const auto [sy,cy]=trig[1];
    const auto [sz,cz]=trig[2];
    const std::array<float,9> rx{1,0,0,0,cx,sx,0,-sx,cx};
    const std::array<float,9> ry{cy,0,-sy,0,1,0,sy,0,cy};
    const std::array<float,9> rz{cz,sz,0,-sz,cz,0,0,0,1};
    return multiply(matrix,multiply(multiply(rx,ry),rz));
}
}
