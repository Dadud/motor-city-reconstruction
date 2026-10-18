#include "mco/input_key_raw.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto code = read(input);
        auto keys = image<128>(input);
        emit(mco::input_key_raw(keys, code));
        emit(keys);
    });
}
