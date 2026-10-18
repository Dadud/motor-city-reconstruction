#include "mco/record_selection_apply.hpp"
#include "mco/camera_context_special.hpp"
#include "mco/selection_state_normalize.hpp"
#include "mco/detail/record_selection.hpp"
#include "mco/record_handler.hpp"
#include "mco/record_pair_match.hpp"
#include <bit>
#include <stdexcept>

namespace mco {
void record_selection_apply(RecordMachine& machine, std::span<const std::byte> pairs,
    std::span<const std::byte, 36> modes, std::span<const std::byte, 12> context,
    std::uint32_t mode, std::uint32_t& counter0, std::uint32_t& counter1) {
    machine.check();
    const bool direct = (mode & 255u) == 0;
    std::uint32_t identifier, handler;
    if (direct) {
        detail::normalize_record_selection(machine);
        identifier = machine.selection_index+4u;
        handler = 0x42f8f0u;
    } else {
        const auto index = std::bit_cast<std::int32_t>(machine.load(record_machine_image::state_flag));
        if (index >= 9) return;
        if (index < 0) throw std::invalid_argument("negative camera mode-table index");
        identifier = detail::read_word(modes, static_cast<std::size_t>(index)*4);
        if (identifier == 0x17u) {
            counter0 = counter1 = 10;
            machine.store(record_machine_image::request_flag,
                          camera_context_special(context) ? 1u : 4u);
            identifier = 12;
        } else {
            machine.store(record_machine_image::request_flag, 0);
        }
        handler = record_handler(identifier);
    }
    auto old_record = machine.record(machine.load(record_machine_image::current_record));
    const auto old_identifier = detail::read_word(old_record, state_record::identifier);
    const bool matched = record_pair_match(pairs, old_identifier, identifier) != 0;
    if (matched) {
        for (std::size_t offset=0; offset<state_record::size; offset+=4)
            machine.store(record_machine_image::snapshot+offset, detail::read_word(old_record, offset));
    } else {
        machine.store(record_machine_image::rollover, 1);
        machine.store(record_machine_image::rollover0, 0);
        machine.store(record_machine_image::rollover1, 0);
        machine.store(record_machine_image::rollover2, 0);
    }
    machine.invoke(detail::read_word(old_record, state_record::callback), 3);
    auto record = machine.record(machine.load(record_machine_image::current_record));
    detail::write_word(record, state_record::identifier, identifier);
    detail::write_word(record, state_record::callback, handler);
    detail::write_word(record, state_record::parameter, 0);
    machine.invoke(handler, 0);
    if (matched) {
        record = machine.record(machine.load(record_machine_image::current_record));
        const auto flags = detail::read_word(record, state_record::flags);
        const auto inherited1 = machine.load(record_machine_image::inherited_word1);
        detail::write_word(record, state_record::flags, flags | 0x20u);
        const auto inherited0 = machine.load(record_machine_image::inherited_word0);
        detail::write_word(record, state_record::inherited_word0, inherited0);
        const auto inherited2 = machine.load(record_machine_image::inherited_word2);
        detail::write_word(record, state_record::inherited_word1, inherited1);
        detail::write_word(record, state_record::inherited_word2, inherited2);
    }
    if (direct) machine.store(record_machine_image::request_flag, 0);
}
}
