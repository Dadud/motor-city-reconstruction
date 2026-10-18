#include "camera_cycle_cases.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        if(cell_io::read(input)!=1) throw std::invalid_argument("cycle lifecycle viewport");
        auto subjects=cell_io::image<120>(input);
        auto fixture=selection_cases::Fixture::read(input);
        auto machine=fixture.machine();
        cycle_cases::lifecycle(fixture,machine,subjects);
        fixture.emit(machine);
        cell_io::emit(subjects);
    });
}
