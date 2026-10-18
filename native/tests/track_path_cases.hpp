#pragma once
#include "cell_io.hpp"
#include "mco/nearest_path_point.hpp"
#include "mco/path_side.hpp"
namespace path_cases {
inline void compare(std::istream& input,unsigned operation) {
    const auto a=cell_io::read(input),b=cell_io::read(input),size=cell_io::read(input);
    if(size==0 || size>32) throw std::invalid_argument("path fixture size");
    std::array<float,3> position{};
    std::array<std::array<float,3>,32> points{};
    for(auto& v:position) v=std::bit_cast<float>(cell_io::read(input));
    for(auto& point:points) for(auto& v:point) v=std::bit_cast<float>(cell_io::read(input));
    const auto view=std::span<const std::array<float,3>>(points.data(),size);
    cell_io::emit(operation==0 ? mco::nearest_path_point(view,position,a,std::bit_cast<std::int32_t>(b)) :
                               mco::path_side(view,position,a));
    for(auto v:position) cell_io::emit(std::bit_cast<std::uint32_t>(v));
    for(auto point:points) for(auto v:point) cell_io::emit(std::bit_cast<std::uint32_t>(v));
}
}
