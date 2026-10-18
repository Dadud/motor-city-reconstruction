#include "mco/zero_flag.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto value = read(input);
        emit(mco::zero_flag(value));
    });
}
