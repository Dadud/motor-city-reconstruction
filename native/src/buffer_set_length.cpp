#include "mco/buffer_set_length.hpp"
#include <stdexcept>
namespace mco {
void buffer_set_length(std::span<std::byte> buffer, std::uint32_t length,
                       std::uint32_t &stored_length) {
    if (length >= buffer.size())
        throw std::out_of_range("length terminator outside buffer");
    stored_length = length;
    buffer[length] = std::byte{0};
}
}
