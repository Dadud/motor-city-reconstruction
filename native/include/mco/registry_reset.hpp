#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x407550; Reset the registry table: cleared counters and one live sentinel record.
void registry_reset(std::span<std::byte> registry);
}
