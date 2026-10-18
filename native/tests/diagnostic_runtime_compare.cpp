#include "mco/diagnostic_runtime.hpp"
#include "diagnostic_runtime_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        diagnostic_runtime_cases::compare(input);
    });
}
