#include "mco/record_should_retain.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto tick = read(input);
        const auto record = image<272>(input);
        const auto request = image<32>(input);
        emit(mco::record_should_retain(record, request, tick));
        emit(record);
        emit(request);
    });
}
