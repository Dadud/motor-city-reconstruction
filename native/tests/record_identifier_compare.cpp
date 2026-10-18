#include "mco/record_identifier.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto record = image<272>(input);
        emit(mco::record_identifier(record));
        emit(record);
    });
}
