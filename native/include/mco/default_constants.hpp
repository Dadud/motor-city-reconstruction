#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x42cae0; Reset three floating-point defaults.
std::array<std::uint32_t,3> default_constants();
}
