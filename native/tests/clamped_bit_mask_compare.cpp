#include "mco/clamped_bit_mask.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto index = std::bit_cast<std::int32_t>(read(input));
        emit(mco::clamped_bit_mask(index));
    });
}
