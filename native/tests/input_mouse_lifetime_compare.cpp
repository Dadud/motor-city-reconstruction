#include "mco/input_mouse_lifetime.hpp"
#include "input_mouse_lifetime_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        input_mouse_lifetime_cases::compare(input);
    });
}
