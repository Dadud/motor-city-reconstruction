#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x4154c0; Store a buffer length and write its trailing zero byte.
void buffer_set_length(std::span<std::byte> buffer, std::uint32_t length, std::uint32_t &stored_length);
}
