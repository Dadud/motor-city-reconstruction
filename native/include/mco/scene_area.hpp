#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x483450; Scene-area query supplying startup record 0xd4.
float scene_area(std::uint32_t owner, std::uint32_t parameter, std::uint32_t turn_limit, std::uint32_t turn_scale, std::uint32_t context);
}
