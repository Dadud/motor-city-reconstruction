#include "selection_controller_cases.hpp"
#include <stdexcept>
int main() {
    selection_cases::Fixture fixture;
    fixture.count=3; fixture.presets={2,3,4};
    mco::detail::write_word(fixture.modes,8,23);
    mco::detail::write_word(fixture.context,0,18);
    mco::detail::write_word(fixture.pairs,0,24);
    mco::detail::write_word(fixture.pairs,4,6);
    mco::detail::write_word(fixture.pairs,8,6);
    mco::detail::write_word(fixture.pairs,12,12);
    mco::detail::write_word(fixture.pairs,16,0xffffffffu);
    auto machine=fixture.machine();
    selection_cases::lifecycle(fixture,machine);
    const auto record=machine.record(machine.load(record_machine_image::current_record));
    if(fixture.logs.size()!=5 || fixture.extra_logs.size()!=5
       || mco::detail::read_word(record,state_record::identifier)!=12
       || machine.selection_presets!=std::array<std::uint32_t,4>{3,2,3,4}
       || machine.selection_index!=2 || machine.selection_slot!=0
       || machine.load(record_machine_image::request_flag)!=1
       || machine.load(record_machine_image::state_flag)!=9
       || fixture.counter0!=10 || fixture.counter1!=10)
        throw std::runtime_error("selection lifecycle state changed");
}
