#include "mco/input_callback_dispatch.hpp"
#include "input_callback_dispatch_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        input_callback_dispatch_cases::compare(input);
    });
}
