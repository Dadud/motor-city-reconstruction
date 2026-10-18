#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x403120; Assign the selected entity field using the original signed remainder.
void entity_word_assign(std::span<std::byte> table, std::int32_t index, std::int32_t count, std::uint32_t side, std::uint32_t value);
}
