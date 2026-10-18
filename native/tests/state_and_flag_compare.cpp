#include "mco/state_and_flag.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto first = read(input);
        const auto second = read(input);
        emit(mco::state_and_flag(first, second));
    });
}
