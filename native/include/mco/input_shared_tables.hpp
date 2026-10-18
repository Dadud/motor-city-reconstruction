#pragma once
#include "mco/layouts.hpp"
#include <array>
#include <bit>
#include <cstdint>
#include <span>
namespace mco {
// Shared observed storage beginning at original 0x8c8748, not a recovered class.
// Mouse words 0x8c8914/18/1c and callback 0x8c8924 overlap translation bytes.
struct InputSharedTables {
    static_assert(std::endian::native==std::endian::little,
                  "shared typed translation storage requires little-endian words");
    std::array<std::uint32_t,scan_translation_tables::size/4> words{};
    auto image(){return std::as_writable_bytes(std::span(words));}
    auto image()const{return std::as_bytes(std::span(words));}
    std::uint32_t& mouse_mode(){return words[460/4];}
    std::uint32_t& mouse_state8(){return words[464/4];}
    std::uint32_t& mouse_state9(){return words[468/4];}
};
}
