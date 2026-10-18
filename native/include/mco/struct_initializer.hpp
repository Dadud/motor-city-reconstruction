#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x403200; Initialize a count and a three-dword state.
void struct_initializer(std::span<std::byte,4> count_image, std::span<std::byte,12> state_image);
}
