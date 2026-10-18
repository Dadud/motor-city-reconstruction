#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/input_translation_state.hpp"
namespace mco {
// Original 0x6f05b0; Translate a queued scan byte using current modifiers, caps state and caller-supplied layout tables.
std::uint32_t input_scan_translate(InputTranslationState &state, std::uint32_t scan, std::uint32_t extended);
}
