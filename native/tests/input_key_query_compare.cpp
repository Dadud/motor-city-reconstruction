#include "mco/input_key_query.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto code = read(input);
        const auto press_only = read(input);
        auto keys = image<128>(input);
        auto latches = image<512>(input);
        emit(mco::input_key_query(keys, latches, code, press_only));
        emit(keys);
        emit(latches);
    });
}
