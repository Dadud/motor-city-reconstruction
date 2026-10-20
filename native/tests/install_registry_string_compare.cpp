#include "mco/install_registry_string.hpp"
#include "install_registry_string_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        install_registry_string_cases::compare(input);
    });
}
