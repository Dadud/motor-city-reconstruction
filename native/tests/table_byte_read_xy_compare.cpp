#include "mco/table_byte_read_xy.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto row = std::bit_cast<std::int32_t>(read(input));
        const auto column = std::bit_cast<std::int32_t>(read(input));
        const auto table = image<900>(input);
        emit(mco::table_byte_read_xy(table, row, column));
    });
}
