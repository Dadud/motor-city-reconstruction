#include "mco/window_handler_register.hpp"
#include "window_registration_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        window_registration_cases::compare(input);
    });
}
