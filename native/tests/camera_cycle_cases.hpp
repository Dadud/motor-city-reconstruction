#pragma once
#include "selection_controller_cases.hpp"
#include "mco/record_mode_apply.hpp"
#include "mco/record_selection_cycle.hpp"

namespace cycle_cases {
inline void lifecycle(selection_cases::Fixture& fixture,mco::RecordMachine& machine,
                      std::array<std::byte,120>& subjects) {
    mco::record_machine_initialize(machine);
    mco::record_selection_apply(machine,fixture.pairs,fixture.modes,fixture.context,
                               0,fixture.counter0,fixture.counter1);
    mco::record_selection_cycle(machine,fixture.pairs,fixture.modes,fixture.context,
                               0,fixture.counter0,fixture.counter1,subjects,1);
    machine.store(record_machine_image::state_flag,0);
    mco::record_mode_apply(machine,fixture.pairs,fixture.modes,fixture.context,
                          255,fixture.counter0,fixture.counter1,0);
    mco::detail::write_word(subjects,camera_subjects::reference+4,0xffffffffu);
    mco::record_selection_cycle(machine,fixture.pairs,fixture.modes,fixture.context,
                               255,fixture.counter0,fixture.counter1,subjects,1);
    mco::record_selection_cycle(machine,fixture.pairs,fixture.modes,fixture.context,
                               255,fixture.counter0,fixture.counter1,subjects,1);
}
}
