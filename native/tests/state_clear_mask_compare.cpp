#include "mco/state_clear_mask.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto first = read(input);
        const auto second = read(input);
        emit(mco::state_clear_mask(first, second));
    });
}
