#include "mco/input_keyboard_layout.hpp"
#include "input_keyboard_layout_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        input_keyboard_layout_cases::compare(input);
    });
}
