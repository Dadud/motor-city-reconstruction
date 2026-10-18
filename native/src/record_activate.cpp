#include "mco/record_activate.hpp"
#include <bit>
#include <stdexcept>
#include "mco/detail/byte_words.hpp"
#include "mco/layouts.hpp"

namespace mco {
void record_activate(RecordMachine& machine) {
    machine.check();
    const auto current = machine.load(record_machine_image::current_record);
    if (current == 0) return;
    auto record = machine.record(current);
    detail::write_word(record, state_record::flags, detail::read_word(record, state_record::flags) | 0x10u);
    const auto handler = detail::read_word(record, state_record::callback);
    if (handler != 0) machine.invoke(handler, 0);
}
}
