#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x408ea0; Clear five entity fields.
void entity_clear(std::span<std::byte> image);
}
