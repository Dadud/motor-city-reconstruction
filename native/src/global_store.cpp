#include "mco/global_store.hpp"

namespace mco {

// Whole body at 0x406a30: store the second global through the destination
// pointer, then return the third global. The destination is a host image
// because the original writes through an emulated address.
std::uint32_t global_store(std::array<std::byte,4>& destination,
                           std::uint32_t stored_value,
                           std::uint32_t returned_value) {
    for (unsigned k = 0; k < 4; ++k)
        destination[k] = static_cast<std::byte>((stored_value >> (k*8)) & 255);
    return returned_value;
}
}  // namespace mco
