#include "mco/indexed_masked_bit.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto record = read(input);
        const auto index = std::bit_cast<std::int32_t>(read(input));
        const auto records = image<352>(input);
        emit(mco::indexed_masked_bit(records, record, index));
        emit(records);
    });
}
