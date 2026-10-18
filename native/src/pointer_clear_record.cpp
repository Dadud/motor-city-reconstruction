#include "mco/pointer_clear_record.hpp"

#include <stdexcept>

namespace mco {

// Whole body at 0x429420: clear the four bytes behind the pointer, then store
// that pointer in the record global. An empty span represents the original's
// null pointer: neither the target nor the record is changed.
void pointer_clear_record(std::span<std::byte> target, std::uint32_t target_id,
                          std::uint32_t &record) {
    if (target.empty()) return;
    if (target.size() < 4) throw std::invalid_argument("pointer target truncated");
    for (unsigned k = 0; k < 4; ++k)
        target[k] = std::byte{0};
    record = target_id;
}
}  // namespace mco
