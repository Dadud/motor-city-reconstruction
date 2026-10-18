#include "mco/input_queue_resize.hpp"
#include "input_queue_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto requested = read(input);
        auto f = queue_cases::Fixture::read(input);
        auto state = f.state();
        mco::input_queue_resize(state, requested);
        f.emit();
    });
}
