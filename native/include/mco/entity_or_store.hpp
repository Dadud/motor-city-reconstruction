#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x409110; OR a value into the entity field at 0x94 with 0xff000000.
void entity_or_store(std::span<std::byte> image, std::uint32_t value);
}
