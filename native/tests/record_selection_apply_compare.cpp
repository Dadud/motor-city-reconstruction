#include "mco/record_selection_apply.hpp"
#include "selection_controller_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        auto fixture = selection_cases::Fixture::read(input);
        auto machine = fixture.machine();
        mco::record_selection_apply(machine, fixture.pairs, fixture.modes, fixture.context, fixture.mode, fixture.counter0, fixture.counter1);
        fixture.emit(machine);
    });
}
