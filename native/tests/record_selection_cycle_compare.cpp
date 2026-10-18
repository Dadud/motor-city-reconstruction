#include "mco/record_selection_cycle.hpp"
#include "selection_controller_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto viewport = read(input);
        auto subjects = image<120>(input);
        auto f = selection_cases::Fixture::read(input);
        auto machine = f.machine();
        mco::record_selection_cycle(machine, f.pairs, f.modes, f.context, f.mode, f.counter0, f.counter1, subjects, viewport);
        f.emit(machine);
        emit(subjects);
    });
}
