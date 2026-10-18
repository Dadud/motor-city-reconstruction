#include "mco/record_activate.hpp"
#include <stdexcept>
int main() {
    std::array<std::byte,0x780> bytes{};
    mco::RecordMachine machine{bytes,{0,0,0,0},0,0,nullptr,nullptr};
    mco::record_activate(machine);
    machine.store(record_machine_image::current_record, 0x98baf8);
    mco::record_activate(machine);
    if (mco::detail::read_word(machine.record(0x98baf8),state_record::flags) != 0x10)
        throw std::runtime_error("null callback must still preserve the active flag");
    mco::detail::write_word(machine.record(0x98baf8),state_record::callback,0x432180);
    try { mco::record_activate(machine); }
    catch (const std::invalid_argument&) { return 0; }
    throw std::runtime_error("an unbound real handler must not become a silent no-op");
}
