#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x42cad0; Assign one original global from the supplied value.
void counter_assign(std::uint32_t &destination, std::uint32_t value);
}
