#include "mco/record_transition.hpp"
#include "record_machine_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto identifier = read(input);
        const auto handler = read(input);
        const auto push = read(input);
        const auto parameter = read(input);
        const auto pairs = image<64>(input);
        auto fixture = record_cases::Fixture::read(input);
        auto machine = fixture.machine();
        mco::record_transition(machine, pairs, identifier, handler, push, parameter);
        fixture.emit(machine);
    });
}
