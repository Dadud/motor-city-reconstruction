#include "mco/camera_matrix_rotation.hpp"
#include <array>
#include <cmath>
#include <stdexcept>
namespace mco {
void camera_matrix_rotation(std::span<const float,9> source,float turns,
                            std::span<float,9> destination,std::uint32_t axis) {
    if(axis>2 || !std::isfinite(turns) || std::abs(turns)>1024)
        throw std::invalid_argument("unsupported camera rotation axis/turns");
    const auto sa=reinterpret_cast<std::uintptr_t>(source.data());
    const auto da=reinterpret_cast<std::uintptr_t>(destination.data());
    if(sa!=da && (sa<da ? da-sa : sa-da)<9*sizeof(float))
        throw std::invalid_argument("partially overlapping camera matrices");
    for(auto value:source) if(!std::isfinite(value) || std::abs(value)>1e20f)
        throw std::invalid_argument("unsupported camera matrix value");
    // Original double conversion constant; trig results stored as float first.
    constexpr double radians_per_turn=6.283185482025146484375;
    const double angle=static_cast<double>(turns)*radians_per_turn;
    const double sine=static_cast<float>(std::sin(angle));
    const double cosine=static_cast<float>(std::cos(angle));
    std::array<float,9> saved;
    if(source.data()==destination.data()) {
        for(unsigned i=0;i<9;++i) saved[i]=source[i];
        source=saved;
    }
    // Original multiply/add chains round only at each final float store.
    for(unsigned column=0;column<3;++column) {
        const double a=source[column],b=source[3+column],c=source[6+column];
        if(axis==0) {
            destination[column]=source[column];
            destination[3+column]=static_cast<float>(b*cosine+c*sine);
            destination[6+column]=static_cast<float>(c*cosine-b*sine);
        } else if(axis==1) {
            destination[3+column]=source[3+column];
            destination[column]=static_cast<float>(cosine*a-c*sine);
            destination[6+column]=static_cast<float>(sine*a+c*cosine);
        } else {
            destination[6+column]=source[6+column];
            destination[column]=static_cast<float>(cosine*a+b*sine);
            destination[3+column]=static_cast<float>(b*cosine-sine*a);
        }
    }
}
}
