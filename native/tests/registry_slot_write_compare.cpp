#include "mco/registry_slot_write.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto slot = read(input);
        const auto first = read(input);
        const auto second = read(input);
        const auto third = read(input);
        auto registry = image<0x1804>(input);
        mco::registry_slot_write(registry, slot, first, second, third);
        emit(registry);
    });
}
