#include "mco/input_device_state.hpp"
#include "input_device_state_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        input_device_state_cases::compare(input);
    });
}
