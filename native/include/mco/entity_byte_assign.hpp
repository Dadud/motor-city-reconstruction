#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x403160; Assign the selected entity field using the original signed remainder.
void entity_byte_assign(std::span<std::byte> table, std::int32_t index, std::int32_t count, std::uint32_t side, std::uint32_t value);
}
