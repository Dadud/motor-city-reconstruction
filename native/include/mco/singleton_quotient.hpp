#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x405910; Wave-0 singleton-divide leaf.
std::int32_t singleton_quotient(std::int32_t dividend, std::uint32_t primary, std::uint32_t fallback);
}
