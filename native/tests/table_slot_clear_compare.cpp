#include "mco/table_slot_clear.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto slot = read(input);
        const auto present = image<256>(input);
        auto targets = image<3072>(input);
        std::array<std::span<std::byte>,256> table{};
        for (std::size_t k = 0; k < table.size(); ++k)
            if (present[k] != std::byte{0}) table[k] = std::span<std::byte>(targets.data()+k*12,12);
        mco::table_slot_clear(table, slot);
        emit(targets);
    });
}
