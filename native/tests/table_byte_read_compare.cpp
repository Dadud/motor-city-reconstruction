#include "mco/table_byte_read.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto index = read(input);
        const auto table = image<256>(input);
        emit(mco::table_byte_read(table, std::bit_cast<std::int32_t>(index)));
    });
}
