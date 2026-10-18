#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x4082c0; Clear through a fallback pointer and return a primary global.
std::uint32_t clear_through(std::span<std::byte> fallback_target, std::uint32_t primary);
}
