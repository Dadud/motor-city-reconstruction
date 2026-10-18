#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x435270; Select an original callback identity from a record identifier.
std::uint32_t record_handler(std::uint32_t identifier);
}
