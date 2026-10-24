#pragma once
#include <cstddef>
#include <cstdint>
#include <functional>
#include <span>

namespace mco {
// Original 0x415410, unique inline-buffer in-place branch only.
std::uint32_t assign_inline_buffer(std::span<std::byte> destination,
                                  std::span<const std::byte> source,
                                  std::uint32_t length,
                                  std::uint32_t capacity);

struct BufferRecord {
  // Includes the byte immediately before the original data pointer.
  std::span<std::byte> storage;
  std::uint32_t length;
  std::uint32_t capacity;
};

using BufferAllocator = std::function<std::span<std::byte>(std::uint32_t)>;
using BufferRelease = std::function<void(std::span<std::byte>)>;

// Mapped normal paths of 0x415410 with caller-supplied heap boundaries.
std::uint32_t assign_buffer(BufferRecord& record,
                            std::span<const std::byte> source,
                            std::uint32_t length,
                            const BufferAllocator& allocate,
                            const BufferRelease& release);
}
