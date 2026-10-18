#include "mco/registry_slot_used.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto slot = read(input);
        const auto registry = image<0x1804>(input);
        emit(mco::registry_slot_used(registry, slot));
    });
}
