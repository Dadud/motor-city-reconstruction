#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x583a90; Translate supported key-down messages to the original packed character codes.
std::uint32_t input_key_translate(std::uint32_t message, std::uint32_t key);
}
