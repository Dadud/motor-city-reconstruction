#include "mco/table_read_b.hpp"
#include <stdexcept>

namespace mco {

// Whole body at 0x42f070: dword[index*4] from the fixed table at 0x98bae0.
std::uint32_t table_read_b(const std::span<const std::byte> table,
                           std::uint32_t index) {
    const size_t offset = static_cast<size_t>(index)*4;
    if (offset+4 > table.size())
        throw std::invalid_argument("table read index outside the table");
    return static_cast<std::uint32_t>(table[offset])
        | static_cast<std::uint32_t>(table[offset+1]) << 8
        | static_cast<std::uint32_t>(table[offset+2]) << 16
        | static_cast<std::uint32_t>(table[offset+3]) << 24;
}
}  // namespace mco
