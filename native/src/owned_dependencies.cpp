#include "mco/owned_dependencies.hpp"

#include <bit>
#include <limits>
#include <stdexcept>

namespace mco {
namespace {
std::uint32_t read_u32(const OwnedPartSlot& slot, std::size_t offset) {
    std::uint32_t value = 0;
    for (std::size_t i = 0; i < 4; ++i)
        value |= static_cast<std::uint32_t>(slot[offset + i]) << (8 * i);
    return value;
}
std::int32_t read_i32(const OwnedPartSlot& slot, std::size_t offset) {
    return std::bit_cast<std::int32_t>(read_u32(slot, offset));
}
void write_i32(OwnedPartSlot& slot, std::size_t offset, std::int32_t value) {
    const auto bits = std::bit_cast<std::uint32_t>(value);
    for (std::size_t i = 0; i < 4; ++i)
        slot[offset + i] = static_cast<std::uint8_t>(bits >> (8 * i));
}
} // namespace

std::vector<OwnedPartSlot> link_owned_dependencies(
    std::span<const OwnedPartSlot> slots,
    std::span<const std::int32_t> resolved_dependency_ids) {
    if (slots.empty()) throw std::invalid_argument("expected nonempty owned-part slots");
    if (slots.size() != resolved_dependency_ids.size())
        throw std::invalid_argument("dependency ID count must match owned-part count");
    if (slots.size() > static_cast<std::size_t>(std::numeric_limits<std::int32_t>::max()))
        throw std::invalid_argument("owned-part indexes must fit int32");
    for (const auto& slot : slots) {
        const auto parent = read_i32(slot, 0x600);
        if (parent < 0 || static_cast<std::size_t>(parent) >= slots.size())
            throw std::invalid_argument("owned-part parent index references nonexistent slot");
    }
    const bool root_absent = read_u32(slots.front(), 0x5f8) == 0;
    std::vector<OwnedPartSlot> result(slots.begin(), slots.end());
    for (std::size_t index = 0; index < slots.size(); ++index) {
        const auto dependency_id = resolved_dependency_ids[index];
        if (dependency_id == 0) write_i32(result[index], 0x604, 0);
        else {
            const auto attachment = read_i32(slots[index], 0x61c);
            for (std::size_t candidate = 0; candidate < slots.size(); ++candidate) {
                const auto candidate_attachment = read_i32(slots[candidate], 0x61c);
                if (read_i32(slots[candidate], 0) == dependency_id &&
                    (candidate_attachment == 0 || candidate_attachment == attachment))
                    write_i32(result[index], 0x604, static_cast<std::int32_t>(candidate));
            }
        }
        const auto abstract_id = read_i32(slots[index], 0);
        const auto parent = static_cast<std::size_t>(read_i32(slots[index], 0x600));
        if (root_absent || abstract_id == 2001 || abstract_id == 20001 || abstract_id == 6001 ||
            read_i32(slots[parent], 0) == 6001)
            write_i32(result[index], 0x634, 0);
    }
    return result;
}
} // namespace mco
