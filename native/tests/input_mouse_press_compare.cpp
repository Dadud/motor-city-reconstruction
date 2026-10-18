#include "mco/input_mouse_press.hpp"
#include "mouse_input_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        mouse_input_cases::compare(input,2);
    });
}
