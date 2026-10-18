#include "mco/input_queue_peek.hpp"
#include <stdexcept>
#include "mco/detail/input_queue_consume.hpp"

namespace mco {

// Decompiled pseudocode of 0x583160, kept as the implementation draft.
// The oracle against the original, not this text, decides correctness.


std::uint32_t input_queue_peek(InputKeyQueue &queue, InputTranslationState &translation) {
    return detail::input_queue_consume(queue,translation,false);
}

}  // namespace mco
