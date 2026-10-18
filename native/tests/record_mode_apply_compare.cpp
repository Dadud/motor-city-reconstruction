#include "mco/record_mode_apply.hpp"
#include "selection_controller_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto index = read(input);
        auto f = selection_cases::Fixture::read(input);
        auto machine = f.machine();
        mco::record_mode_apply(machine, f.pairs, f.modes, f.context, f.mode, f.counter0, f.counter1, index);
        f.emit(machine);
    });
}
