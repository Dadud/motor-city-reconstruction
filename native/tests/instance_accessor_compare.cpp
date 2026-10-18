#include "mco/instance_accessor.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto first = read(input);
        const auto second = read(input);
        emit(mco::instance_accessor(first, second));
    });
}
