#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x41bf80; Increment a monotonically increasing counter.
std::uint32_t counter_increment(std::uint32_t counter);
}
