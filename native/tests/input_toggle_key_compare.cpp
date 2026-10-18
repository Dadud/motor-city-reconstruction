#include "mco/input_toggle_key.hpp"
#include "input_toggle_key_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        input_toggle_key_cases::compare(input);
    });
}
