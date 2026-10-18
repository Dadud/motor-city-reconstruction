#include "mco/record_machine_initialize.hpp"
#include <bit>
#include <stdexcept>
#include <initializer_list>
#include "mco/detail/byte_words.hpp"
#include "mco/layouts.hpp"

namespace mco {
void record_machine_initialize(RecordMachine& machine) {
    machine.check();
    for (std::size_t offset = 0; offset < 6*state_record::size; offset += 4)
        machine.store(record_machine_image::records+offset, 0);
    const auto first = record_machine_address+static_cast<std::uint32_t>(record_machine_image::records);
    machine.store(record_machine_image::current_record, first);
    machine.store(record_machine_image::base_record, first);
    auto record = machine.record(first);
    detail::write_word(record, state_record::identifier, 24);
    detail::write_word(record, state_record::callback, 0x432180);
    detail::write_word(record, state_record::initial_sentinel, 0xffffffffu);
    machine.invoke(0x432180, 0);
    for (auto offset : {record_machine_image::state_flag,record_machine_image::request_flag,
         record_machine_image::rollover,record_machine_image::rollover0,
         record_machine_image::rollover1,record_machine_image::rollover2,
         record_machine_image::after_stack_flag}) machine.store(offset, 0);
    machine.selection_slot = 0;
    if (std::bit_cast<std::int32_t>(machine.selection_presets[0]) > 0)
        machine.selection_index = machine.selection_presets[0]-1u;
}
}
