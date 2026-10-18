#include "selection_controller_cases.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        auto fixture=selection_cases::Fixture::read(input);
        auto machine=fixture.machine();
        selection_cases::lifecycle(fixture,machine);
        fixture.emit(machine);
    });
}
