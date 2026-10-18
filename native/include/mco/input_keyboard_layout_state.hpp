#pragma once
#include "mco/input_key_queue.hpp"
namespace mco {
inline constexpr std::uint32_t keyboard_scan_remap_identity=0x8c8930;
using InputKeyboardType=std::uint32_t (*)(InputKeyQueue&,std::uint32_t kind,void* user);
struct InputKeyboardLayoutPlatform {InputKeyboardType query{};void* user{};};
// The selected 128-byte remap aliases the existing scan-translation image.
inline std::span<const std::byte,128> input_keyboard_remap(std::span<const std::byte,scan_translation_tables::size> tables) {
    return std::span<const std::byte,128>(tables.data()+scan_translation_tables::keyboard_remap,128);
}
}
