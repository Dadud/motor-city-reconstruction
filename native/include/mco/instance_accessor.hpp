#pragma once
#include <cstdint>
namespace mco {
// Original 0x405900; Global instance accessor with a fallback default.
// Two original globals supply the candidate and the fallback, because the
// returned address is an emulated 32-bit value and never a host pointer.
std::uint32_t instance_accessor(std::uint32_t primary, std::uint32_t fallback);
}