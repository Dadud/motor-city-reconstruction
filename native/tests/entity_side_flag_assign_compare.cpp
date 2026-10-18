#include "mco/entity_side_flag_assign.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto present = read(input);
        const auto index = std::bit_cast<std::int32_t>(read(input));
        const auto count = std::bit_cast<std::int32_t>(read(input));
        const auto side = read(input);
        const auto value = read(input);
        auto table = image<256>(input);
        mco::entity_side_flag_assign(present ? std::span<std::byte>(table) : std::span<std::byte>{}, index, count, side, value);
        emit(table);
    });
}
