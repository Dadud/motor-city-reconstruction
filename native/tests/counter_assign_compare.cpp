#include "mco/counter_assign.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        auto destination = read(input);
        const auto value = read(input);
        mco::counter_assign(destination, value);
        emit(destination);
    });
}
