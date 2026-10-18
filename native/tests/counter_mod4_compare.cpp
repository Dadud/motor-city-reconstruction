#include "mco/counter_mod4.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto value = read(input);
        emit(mco::counter_mod4(value));
    });
}
