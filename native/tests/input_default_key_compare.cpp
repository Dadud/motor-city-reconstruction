#include "mco/input_default_key.hpp"
#include "input_default_key_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        input_default_key_cases::compare(input);
    });
}
