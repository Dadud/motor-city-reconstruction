#include "mco/record_transition.hpp"
#include <bit>
#include <stdexcept>
#include "mco/detail/byte_words.hpp"
#include "mco/layouts.hpp"
#include "mco/record_pair_match.hpp"

namespace mco {
void record_transition(RecordMachine& machine, std::span<const std::byte> pairs,
                       std::uint32_t identifier, std::uint32_t handler,
                       std::uint32_t push, std::uint32_t parameter) {
    machine.check();
    const auto old_address = machine.load(record_machine_image::current_record);
    auto old_record = machine.record(old_address);
    // The original reads this unconditionally before its later null branch.
    const auto old_identifier = detail::read_word(old_record, state_record::identifier);
    const bool matched = record_pair_match(pairs, old_identifier, identifier) != 0;
    if (matched) {
        for (std::size_t offset = 0; offset < state_record::size; offset += 4)
            machine.store(record_machine_image::snapshot+offset, detail::read_word(old_record, offset));
    } else {
        machine.store(record_machine_image::rollover, 1);
        machine.store(record_machine_image::rollover0, 0);
        machine.store(record_machine_image::rollover1, 0);
        machine.store(record_machine_image::rollover2, 0);
    }
    if (push == 0) {
        machine.invoke(detail::read_word(old_record, state_record::callback), 3);
    } else {
        const auto next = old_address == 0 ? machine.load(record_machine_image::base_record)
            : old_address+static_cast<std::uint32_t>(state_record::size);
        machine.store(record_machine_image::current_record, next);
    }
    auto record = machine.record(machine.load(record_machine_image::current_record));
    detail::write_word(record, state_record::identifier, identifier);
    detail::write_word(record, state_record::callback, handler);
    detail::write_word(record, state_record::parameter, parameter);
    machine.invoke(detail::read_word(record, state_record::callback), 0);
    if (matched) {
        // Callback zero may redirect the global current pointer a second time.
        record = machine.record(machine.load(record_machine_image::current_record));
        const auto inherited0 = machine.load(record_machine_image::inherited_word0);
        detail::write_word(record, state_record::flags, detail::read_word(record, state_record::flags) | 0x20u);
        const auto inherited1 = machine.load(record_machine_image::inherited_word1);
        detail::write_word(record, state_record::inherited_word0, inherited0);
        const auto inherited2 = machine.load(record_machine_image::inherited_word2);
        detail::write_word(record, state_record::inherited_word1, inherited1);
        detail::write_word(record, state_record::inherited_word2, inherited2);
    }
}
}
