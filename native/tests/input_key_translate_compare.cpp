#include "mco/input_key_translate.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto message = read(input);
        const auto key = read(input);
        emit(mco::input_key_translate(message, key));
    });
}
