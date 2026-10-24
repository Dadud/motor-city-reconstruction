#include "mco/string_buffer.hpp"
#include "mco/buffer_set_length.hpp"
#include <algorithm>
#include <array>
#include <stdexcept>
#include <vector>

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

std::uint32_t assign_buffer(BufferRecord& record,
                            std::span<const std::byte> source,
                            std::uint32_t length,
                            const BufferAllocator& allocate,
                            const BufferRelease& release) {
  if (length > 0xfffffffdu || source.size() < length || !allocate || !release)
    throw std::invalid_argument("invalid string-buffer assignment inputs");
  auto old = record.storage;
  if (!old.empty() && old.size() < std::size_t(record.capacity) + 2)
    throw std::invalid_argument("buffer storage omits header or terminator");
  const auto old_length = record.length;
  const auto old_capacity = record.capacity;
  const auto header = old.empty() ? std::uint8_t{0} :
      std::to_integer<std::uint8_t>(old[0]);
  const bool unique = old.empty() || header == 0 || header == 0xff;

  if (unique) {
    if (length == 0) {
      if (!old.empty()) release(old);
      record.storage = {};
      record.length = record.capacity = 0;
      return 0;
    }
    if (!old.empty() && old_capacity < 0x20 && length <= old_capacity) {
      assign_inline_buffer(old.subspan(1), source, length, old_capacity);
      record.length = length;
      return length;
    }
    if (!old.empty()) {
      release(old);
      record.storage = {};
      record.length = record.capacity = 0;
    }
  } else if (length == 0) {
    old[0] = std::byte((header - 1) & 0xff);
    record.storage = {};
    record.length = record.capacity = 0;
    return 0;
  }

  auto rounded = length | 0x1fu;
  if (rounded > 0xfffffffdu) rounded = length;
  auto allocation_size = rounded + 2;
  if (allocation_size & 0x80000000u) allocation_size = 0;
  std::vector<std::byte> source_copy(source.begin(), source.begin() + length);
  auto fresh = allocate(allocation_size);
  if (fresh.size() < allocation_size || fresh.size() < std::size_t(length) + 2)
    throw std::invalid_argument("allocator returned undersized storage");
  fresh[0] = std::byte{0};

  // Preserve the old prefix before the final assignment copy, as 0x415bda does.
  const auto copied = old.empty() ? 0u : std::min(old_length, length);
  if (copied != 0)
    std::copy_n(old.begin() + 1, copied, fresh.begin() + 1);
  if (!old.empty() && !unique)
    old[0] = std::byte((header - 1) & 0xff);
  std::copy(source_copy.begin(), source_copy.end(), fresh.begin() + 1);
  fresh[length + 1] = std::byte{0};
  record.storage = fresh;
  record.length = length;
  record.capacity = length;
  return length;
}
}
