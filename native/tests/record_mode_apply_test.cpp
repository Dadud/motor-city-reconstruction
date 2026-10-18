#include "selection_controller_cases.hpp"
#include "mco/record_mode_apply.hpp"
#include <stdexcept>
int main() {
    selection_cases::Fixture f;
    auto machine=f.machine();
    machine.store(record_machine_image::current_record,0x98baf8);
    auto record=machine.record(0x98baf8);
    mco::detail::write_word(record,state_record::identifier,24);
    mco::detail::write_word(record,state_record::callback,0x432180);
    mco::detail::write_word(f.pairs,0,0xffffffffu);
    mco::detail::write_word(f.modes,8,23);
    mco::record_mode_apply(machine,f.pairs,f.modes,f.context,0,f.counter0,f.counter1,2);
    if(mco::detail::read_word(record,state_record::identifier)!=8
       || machine.load(record_machine_image::request_flag)!=2
       || f.counter0!=10 || f.counter1!=10 || f.logs.size()!=2)
        throw std::runtime_error("direct-mode special selection");
    f.logs.clear();
    machine.store(record_machine_image::current_record,0);
    mco::record_mode_apply(machine,f.pairs,f.modes,f.context,1,f.counter0,f.counter1,9);
    if(!f.logs.empty()) throw std::runtime_error("disabled explicit mode called handler");
    try {mco::record_mode_apply(machine,f.pairs,f.modes,f.context,1,f.counter0,f.counter1,0xffffffffu);}
    catch(const std::invalid_argument&) {return 0;}
    throw std::runtime_error("negative explicit mode accepted");
}
