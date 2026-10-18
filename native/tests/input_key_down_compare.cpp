#include "mco/input_key_down.hpp"
#include "input_queue_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto enabled = read(input);
        const auto window = read(input);
        const auto message = read(input);
        const auto key = read(input);
        const auto bits = read(input);
        auto f = queue_cases::Fixture::read(input);
        auto state = f.state();
        emit(mco::input_key_down(state, f.remap, enabled, window, message, key, bits));
        f.emit();
    });
}
