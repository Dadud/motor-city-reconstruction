#include "mco/input_queue_pop.hpp"
#include <stdexcept>
#include "mco/detail/input_queue_consume.hpp"

namespace mco {

// Decompiled pseudocode of 0x5830c0, kept as the implementation draft.
// The oracle against the original, not this text, decides correctness.


std::uint32_t input_queue_pop(InputKeyQueue &queue, InputTranslationState &translation) {
    return detail::input_queue_consume(queue,translation,true);
}

}  // namespace mco
