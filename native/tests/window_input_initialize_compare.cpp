#include "mco/window_input_initialize.hpp"
#include "window_initialization_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        window_initialization_cases::compare(input);
    });
}
