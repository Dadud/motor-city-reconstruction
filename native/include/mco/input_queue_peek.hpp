#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/input_key_queue.hpp"
#include "mco/input_translation_state.hpp"
namespace mco {
// Original 0x583160; Read the original packed queue result with signed character extension and exact head-advance behavior.
std::uint32_t input_queue_peek(InputKeyQueue &queue, InputTranslationState &translation);
}
