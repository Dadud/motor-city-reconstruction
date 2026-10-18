#include "mco/entity_side_flag.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto present = read(input);
        const auto index = read(input);
        const auto side = read(input);
        const auto table = image<256>(input);
        emit(mco::entity_side_flag(present ? std::span<const std::byte>(table) : std::span<const std::byte>{}, index, static_cast<std::uint32_t>(side)));
        emit(table);
    });
}
