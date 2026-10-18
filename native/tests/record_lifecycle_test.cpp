#include "record_machine_cases.hpp"
#include <stdexcept>
int main() {
    record_cases::Fixture fixture;
    fixture.count = 3;
    fixture.redirect3 = fixture.redirect0 = 0xffffffffu;
    auto machine = fixture.machine();
    const auto result = record_cases::lifecycle(machine);
    if (result != std::array<std::uint32_t,5>{0,0x432bc0,1,1,0}
        || fixture.logs.size() != 3
        || machine.load(record_machine_image::current_record) != 0x98baf8)
        throw std::runtime_error("connected record lifecycle changed");
    const auto child = machine.record(0x98bbf8);
    if (mco::detail::read_word(child, state_record::flags) != 0x30)
        throw std::runtime_error("matched transition and activation flags did not compose");
}
