#include "mco/record_stack_contains.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto base = read(input);
        const auto cursor = read(input);
        const auto identifier = read(input);
        const auto records = image<1296>(input);
        emit(mco::record_stack_contains(records, base, cursor, identifier));
        emit(records);
    });
}
