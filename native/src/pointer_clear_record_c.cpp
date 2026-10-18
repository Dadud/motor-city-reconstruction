#include "mco/pointer_clear_record_c.hpp"
#include "mco/pointer_clear_record.hpp"
namespace mco {
void pointer_clear_record_c(std::span<std::byte> target, std::uint32_t target_id, std::uint32_t &record) {
    pointer_clear_record(target, target_id, record);
}
}
