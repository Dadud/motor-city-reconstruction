#pragma once
#include <span>
#include <cstdint>
#include <cstddef>
#include <stdexcept>
#include "mco/detail/byte_words.hpp"
namespace mco {
using SpatialDiagnostic=void (*)(std::uint32_t message_identity,void* user);
struct SpatialQueryMemory {
    static constexpr std::uint32_t grid_address=0xa559d8;
    std::span<const std::byte,65536> grid;
    std::span<const std::byte> nodes;
    std::uint32_t nodes_address;
    SpatialDiagnostic diagnostic{};
    void* user{};
    std::uint32_t word(std::uint32_t address) const {
        if(address>=grid_address && std::uint64_t(address-grid_address)+4<=grid.size())
            return detail::read_word(grid,address-grid_address);
        if(address>=nodes_address && std::uint64_t(address-nodes_address)+4<=nodes.size())
            return detail::read_word(nodes,address-nodes_address);
        throw std::invalid_argument("spatial node outside supplied memory");
    }
};
}
