#include "mco/registry_reset.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        auto registry = image<0x1804>(input);
        mco::registry_reset(registry);
        emit(registry);
    });
}
