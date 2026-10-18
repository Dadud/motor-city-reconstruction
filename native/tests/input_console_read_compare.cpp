#include "mco/input_console_read.hpp"
#include "input_console_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        input_console_cases::compare(input);
    });
}
