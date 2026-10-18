#include "mco/buffer_copy12_a.hpp"
#include <stdexcept>

namespace mco {

// Whole body at 0x4081c0: three dword copies from the source argument into
// the destination held in ECX.
void buffer_copy12_a(std::span<std::byte,12> destination,
                   const std::span<const std::byte,12> source) {
    for (unsigned k = 0; k < 12; ++k)
        destination[k] = source[k];
}
}  // namespace mco
