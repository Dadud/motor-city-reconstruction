#include "mco/entity_flag3.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto present = read(input);
        const auto index = read(input);
        const auto table = image<256>(input);
        emit(mco::entity_flag3(present ? std::span<const std::byte>(table) : std::span<const std::byte>{}, index));
    });
}
