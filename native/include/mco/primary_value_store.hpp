#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x410c10; Assign one original global from the supplied value.
void primary_value_store(std::uint32_t &destination, std::uint32_t value);
}
