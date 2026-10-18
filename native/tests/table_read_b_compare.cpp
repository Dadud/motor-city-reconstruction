#include "mco/table_read_b.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto index = read(input);
        const auto table = image<256>(input);
        emit(mco::table_read_b(table, index));
    });
}
