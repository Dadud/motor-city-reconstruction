#include "mco/record_machine_initialize.hpp"
#include <stdexcept>
int main() {
    std::array<std::byte,0x780> bytes{};
    mco::RecordMachine machine{bytes,{3,0,0,0},9,8,[](mco::RecordMachine& m, std::uint32_t handler, std::uint32_t event, void*) {
        if (handler != 0x432180 || event != 0) throw std::runtime_error("initial callback changed");
        m.selection_presets[0] = 5;
    },nullptr};
    mco::record_machine_initialize(machine);
    if (machine.selection_index != 4 || machine.selection_slot != 0)
        throw std::runtime_error("selection gate must observe callback mutation");
}
