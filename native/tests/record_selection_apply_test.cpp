#include "selection_controller_cases.hpp"
#include <stdexcept>
int main() {
    selection_cases::Fixture f;
    f.count=5; f.presets={0xffffffffu,8,9}; f.index=0xffffffffu; f.pending=6;
    auto machine=f.machine();
    machine.store(record_machine_image::current_record,0x98baf8);
    auto record=machine.record(0x98baf8);
    mco::detail::write_word(record,state_record::identifier,24);
    mco::detail::write_word(record,state_record::callback,0x432180);
    mco::detail::write_word(f.pairs,0,24); mco::detail::write_word(f.pairs,4,4);
    mco::detail::write_word(f.pairs,8,0xffffffffu);
    mco::record_selection_apply(machine,f.pairs,f.modes,f.context,0,f.counter0,f.counter1);
    if(machine.selection_presets!=std::array<std::uint32_t,4>{1,0xffffffffu,3,4}
       || machine.selection_index!=0 || machine.selection_slot!=2
       || f.logs.size()!=2 || f.logs[0][1]!=3 || f.logs[1][1]!=0
       || mco::detail::read_word(record,state_record::identifier)!=4
       || machine.load(record_machine_image::request_flag)!=0)
        throw std::runtime_error("direct selection lifecycle");
    f.logs.clear(); f.extra_logs.clear();
    mco::detail::write_word(f.modes,0,23); mco::detail::write_word(f.context,0,18);
    machine.store(record_machine_image::state_flag,0);
    mco::record_selection_apply(machine,f.pairs,f.modes,f.context,1,f.counter0,f.counter1);
    if(f.counter0!=10 || f.counter1!=10
       || machine.load(record_machine_image::request_flag)!=1
       || mco::detail::read_word(record,state_record::identifier)!=12)
        throw std::runtime_error("context-driven special selection");
    f.logs.clear();
    machine.store(record_machine_image::state_flag,9);
    machine.store(record_machine_image::current_record,0);
    mco::record_selection_apply(machine,f.pairs,f.modes,f.context,1,f.counter0,f.counter1);
    if(!f.logs.empty()) throw std::runtime_error("disabled mode dispatched");
    machine.store(record_machine_image::state_flag,0xffffffffu);
    try {
        mco::record_selection_apply(machine,f.pairs,f.modes,f.context,1,f.counter0,f.counter1);
    } catch(const std::invalid_argument&) {return 0;}
    throw std::runtime_error("negative mode index accepted");
}
