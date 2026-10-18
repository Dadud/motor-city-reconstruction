#include "mco/pointer_clear_record_b.hpp"
#include "mco/pointer_clear_record.hpp"
namespace mco {
void pointer_clear_record_b(std::span<std::byte> target, std::uint32_t target_id, std::uint32_t &record) {
    pointer_clear_record(target, target_id, record);
}
}
