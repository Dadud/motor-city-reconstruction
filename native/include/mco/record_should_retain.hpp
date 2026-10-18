#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x435840; Decide whether the current record should be retained for a request.
std::uint32_t record_should_retain(std::span<const std::byte> record, std::span<const std::byte> request, std::uint32_t tick);
}
