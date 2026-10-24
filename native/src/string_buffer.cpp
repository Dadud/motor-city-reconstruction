#include "mco/string_buffer.hpp"
#include "mco/buffer_set_length.hpp"
#include <array>
#include <stdexcept>

namespace mco {
std::uint32_t assign_inline_buffer(std::span<std::byte> destination,
                                  std::span<const std::byte> source,
                                  std::uint32_t length,
                                  std::uint32_t capacity) {
  if (length == 0 || length > capacity || capacity >= 0x20 ||
      destination.size() < std::size_t(capacity) + 1 || source.size() < length)
    throw std::invalid_argument("unsupported string-buffer assignment domain");

  std::size_t offset = 0;
  for (std::uint32_t words = length >> 2; words != 0; --words) {
    std::array<std::byte, 4> word{};
    for (std::size_t i = 0; i < word.size(); ++i) word[i] = source[offset + i];
    for (std::size_t i = 0; i < word.size(); ++i) destination[offset + i] = word[i];
    offset += word.size();
  }
  for (std::uint32_t tail = length & 3; tail != 0; --tail, ++offset)
    destination[offset] = source[offset];
  std::uint32_t stored_length = 0;
  buffer_set_length(destination, length, stored_length);
  return stored_length;
}
}
