#include "mco/record_machine_reset.hpp"
#include "record_machine_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        auto fixture = record_cases::Fixture::read(input);
        auto machine = fixture.machine();
        mco::record_machine_reset(machine);
        fixture.emit(machine);
    });
}
