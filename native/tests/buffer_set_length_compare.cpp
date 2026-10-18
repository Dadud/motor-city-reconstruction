#include "mco/buffer_set_length.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        auto length_field = read(input);
        const auto length = read(input);
        auto buffer = image<20>(input);
        mco::buffer_set_length(buffer, length, length_field);
        emit(length_field);
        emit(buffer);
    });
}
