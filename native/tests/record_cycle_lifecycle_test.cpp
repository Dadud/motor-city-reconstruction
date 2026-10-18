#include "camera_cycle_cases.hpp"
#include <stdexcept>
int main() {
    selection_cases::Fixture fixture;
    fixture.count=3;fixture.presets={2,3,4};
    const std::array<std::uint32_t,9> modes{23,4,14,23,4,4,4,4,4};
    for(unsigned k=0;k<9;++k) mco::detail::write_word(fixture.modes,k*4,modes[k]);
    mco::detail::write_word(fixture.context,0,18);
    mco::detail::write_word(fixture.pairs,0,0xffffffffu);
    std::array<std::byte,120> subjects{};
    mco::detail::write_word(subjects,4,0x12345678);
    mco::detail::write_word(subjects,camera_subjects::reference+4,0x12345678);
    auto machine=fixture.machine();
    cycle_cases::lifecycle(fixture,machine,subjects);
    const auto record=machine.record(machine.load(record_machine_image::current_record));
    if(fixture.logs.size()!=11 || machine.selection_index!=1 || machine.selection_slot!=1
       || machine.load(record_machine_image::state_flag)!=3
       || machine.load(record_machine_image::request_flag)!=1
       || mco::detail::read_word(record,state_record::identifier)!=12
       || fixture.counter0!=10 || fixture.counter1!=10)
        throw std::runtime_error("camera cycle lifecycle changed");
}
