#include "mco/record_transition.hpp"
#include <stdexcept>
int main() {
    std::array<std::byte,0x780> bytes{};
    mco::RecordMachine machine{bytes,{0,0,0,0},0,0,[](mco::RecordMachine&,std::uint32_t,std::uint32_t,void*){},nullptr};
    machine.store(record_machine_image::current_record, 0x98baf8);
    machine.store(record_machine_image::base_record, 0x98baf8);
    std::array<std::byte,4> pairs{}; pairs.fill(std::byte{0xff});
    mco::record_transition(machine, pairs, 14, 0x432bc0, 1, 9);
    if (machine.load(record_machine_image::current_record) != 0x98bbf8
        || machine.load(record_machine_image::rollover) != 1)
        throw std::runtime_error("push or fallback rollover changed");
}
