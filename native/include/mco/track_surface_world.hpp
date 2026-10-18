#pragma once
#include "mco/spatial_query_memory.hpp"
#include <array>
#include <bit>
namespace mco {
struct TrackSurfaceWorld {
    SpatialQueryMemory memory;
    std::array<float,2> origin,scale;
    std::uint32_t blocks_address,paths_address;
    std::int32_t last_block,path_count;
    std::uint32_t word(std::uint32_t address) const {return memory.word(address);}
    float real(std::uint32_t address) const {return std::bit_cast<float>(word(address));}
    std::uint16_t half(std::uint32_t address) const {return static_cast<std::uint16_t>(word(address));}
    std::int16_t signed_half(std::uint32_t address) const {return std::bit_cast<std::int16_t>(half(address));}
};
}
