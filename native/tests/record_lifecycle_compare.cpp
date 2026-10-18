#include "record_machine_cases.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        auto fixture = record_cases::Fixture::read(input);
        auto machine = fixture.machine();
        cell_io::emit(record_cases::lifecycle(machine));
        fixture.emit(machine);
    });
}
