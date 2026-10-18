#include "mco/startup_initialize.hpp"
#include "startup_initialize_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        startup_initialize_cases::compare(input);
    });
}
