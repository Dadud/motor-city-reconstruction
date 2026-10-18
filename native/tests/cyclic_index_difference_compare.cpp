#include "mco/cyclic_index_difference.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto first = std::bit_cast<std::int32_t>(read(input));
        const auto second = std::bit_cast<std::int32_t>(read(input));
        const auto count = std::bit_cast<std::int32_t>(read(input));
        const auto mode = read(input);
        emit(std::bit_cast<std::uint32_t>(mco::cyclic_index_difference(first, second, count, mode)));
    });
}
