#include "mco/input_key_release.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto present = read(input);
        const auto enabled = read(input);
        const auto window = read(input);
        const auto target = read(input);
        const auto bits = read(input);
        auto keys = image<256>(input);
        auto remap = image<128>(input);
        emit(mco::input_key_release(keys, remap, present, enabled, window, target, bits));
        emit(keys);
        emit(remap);
    });
}
