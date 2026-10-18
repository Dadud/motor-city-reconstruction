#pragma once
#include "mco/record_machine.hpp"
#include "mco/selection_state_normalize.hpp"

namespace mco::detail {
// Host composition helper, not an additional recovered original entrypoint.
inline void normalize_record_selection(RecordMachine& machine) {
    std::array<std::byte,camera_selection::size> selection{};
    for (std::size_t i=0; i<4; ++i)
        write_word(selection, i*4, machine.selection_presets[i]);
    write_word(selection, camera_selection::selected_index, machine.selection_index);
    write_word(selection, camera_selection::selected_slot, machine.selection_slot);
    selection_state_normalize(selection);
    for (std::size_t i=0; i<4; ++i)
        machine.selection_presets[i] = read_word(selection, i*4);
    machine.selection_index = read_word(selection, camera_selection::selected_index);
    machine.selection_slot = read_word(selection, camera_selection::selected_slot);
}
}
