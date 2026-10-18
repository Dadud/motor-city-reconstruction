#include "mco/record_signed_negate.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        auto record = image<272>(input);
        mco::record_signed_negate(record);
        emit(record);
    });
}
