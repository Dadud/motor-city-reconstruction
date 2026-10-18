#include "mco/input_scan_translate.hpp"
#include "input_translation_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        input_translation_cases::compare(input);
    });
}
