#include "selection_controller_cases.hpp"
#include "mco/record_selection_cycle.hpp"
#include <stdexcept>
int main() {
    selection_cases::Fixture f;
    f.count=1;f.presets={0xffffffffu,0,0};f.index=9;
    std::array<std::byte,120> subjects{};
    auto machine=f.machine();
    machine.store(record_machine_image::current_record,0x98baf8);
    auto record=machine.record(0x98baf8);
    mco::detail::write_word(record,state_record::identifier,4);
    mco::detail::write_word(record,state_record::callback,0x42f8f0);
    mco::detail::write_word(f.pairs,0,0xffffffffu);
    mco::record_selection_cycle(machine,f.pairs,f.modes,f.context,0,f.counter0,f.counter1,subjects,0);
    if(machine.selection_slot!=1 || machine.selection_index!=4 || !f.logs.empty())
        throw std::runtime_error("negative preset must stop without transition");
    machine.selection_presets={1,0,0,0};machine.selection_slot=0;
    mco::record_selection_cycle(machine,f.pairs,f.modes,f.context,0,f.counter0,f.counter1,subjects,0);
    if(machine.selection_slot!=0 || machine.selection_index!=0 || f.logs.size()!=2)
        throw std::runtime_error("zero presets must wrap to first slot");
    f.logs.clear();
    mco::detail::write_word(record,state_record::identifier,24);
    mco::detail::write_word(subjects,0x3c,1);
    for(unsigned k=0;k<9;++k) mco::detail::write_word(f.modes,k*4,4);
    machine.store(record_machine_image::state_flag,0);
    bool rejected=false;
    try {mco::record_selection_cycle(machine,f.pairs,f.modes,f.context,0,f.counter0,f.counter1,subjects,0);}
    catch(const std::invalid_argument&) {rejected=true;}
    if(!rejected || machine.load(record_machine_image::state_flag)!=0 || !f.logs.empty())
        throw std::runtime_error("nonterminating table should reject without storing index");
    mco::detail::write_word(f.modes,12,23);
    mco::record_selection_cycle(machine,f.pairs,f.modes,f.context,0,f.counter0,f.counter1,subjects,0);
    if(machine.load(record_machine_image::state_flag)!=3
       || machine.load(record_machine_image::request_flag)!=2
       || mco::detail::read_word(record,state_record::identifier)!=8)
        throw std::runtime_error("nonreference subject must skip fours");
    f.logs.clear();
    mco::detail::write_word(record,state_record::identifier,10);
    mco::record_selection_cycle(machine,f.pairs,f.modes,f.context,0,f.counter0,f.counter1,{},0xffffffffu);
    if(!f.logs.empty()) throw std::runtime_error("blocked identifier read subject table");
}
