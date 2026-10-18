#pragma once
#include "mco/detail/byte_words.hpp"
#include "mco/layouts.hpp"
#include <span>
#include <array>
#include <cstdint>
#include <stdexcept>

namespace mco {
inline constexpr std::uint32_t record_machine_address = 0x98b9a0;
struct RecordMachine;
using RecordCallback = void (*)(RecordMachine&, std::uint32_t handler,
                                std::uint32_t event, void* user);

// Original-address identities map into caller-owned bytes; no process address
// is cast to a host pointer. A callback may mutate bytes and scalar globals,
// while the backing span remains fixed for the operation.
struct RecordMachine {
    const std::span<std::byte> bytes;
    // Four preset values at 0x9aba98..0x9abaa4.
    std::array<std::uint32_t, 4> selection_presets;
    std::uint32_t selection_index;
    std::uint32_t selection_slot;
    RecordCallback callback;
    void* user;

    void check() const {
        if (bytes.size() < record_machine_image::size
            || bytes.size() > 0x9aba98u-record_machine_address)
            throw std::invalid_argument("record machine image truncated");
    }
    std::uint32_t load(std::size_t offset) const {
        return detail::read_word(bytes, offset);
    }
    void store(std::size_t offset, std::uint32_t value) {
        detail::write_word(bytes, offset, value);
    }
    std::span<std::byte> record(std::uint32_t address) const {
        constexpr auto base = record_machine_address;
        if (address < base || std::uint64_t(address-base)+state_record::size > bytes.size())
            throw std::invalid_argument("record address outside supplied machine image");
        return bytes.subspan(address-base, state_record::size);
    }
    void invoke(std::uint32_t handler, std::uint32_t event) {
        if (!handler || !callback)
            throw std::invalid_argument("record callback implementation required");
        callback(*this, handler, event, user);
    }
};
}  // namespace mco
