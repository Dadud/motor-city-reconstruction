#pragma once
#include "cell_io.hpp"
#include "mco/spatial_grid_lookup.hpp"
#include <vector>
namespace spatial_grid_cases {
inline void compare(std::istream& input) {
    std::array<float,3> position{};
    std::array<float,2> origin{},scale{};
    for(auto& v:position) v=std::bit_cast<float>(cell_io::read(input));
    for(auto& v:origin) v=std::bit_cast<float>(cell_io::read(input));
    for(auto& v:scale) v=std::bit_cast<float>(cell_io::read(input));
    const auto slot=cell_io::read(input);
    if(slot>=4096) throw std::invalid_argument("spatial root slot");
    const auto root=cell_io::image<16>(input);
    const auto nodes=cell_io::image<320>(input);
    std::array<std::byte,65536> grid{};
    for(unsigned i=0;i<16;++i) grid[slot*16+i]=root[i];
    std::vector<std::uint32_t> diagnostics;
    mco::SpatialQueryMemory memory{grid,nodes,0x71001000,
        [](std::uint32_t message,void* user) {
            static_cast<std::vector<std::uint32_t>*>(user)->push_back(message);
        },&diagnostics};
    cell_io::emit(mco::spatial_grid_lookup(memory,position,origin,scale));
    cell_io::emit(static_cast<std::uint32_t>(diagnostics.size()));
    for(auto message:diagnostics) cell_io::emit(message);
    for(unsigned i=0;i<16;++i) cell_io::emit(std::to_integer<std::uint32_t>(grid[slot*16+i]));
    cell_io::emit(nodes);
}
}
