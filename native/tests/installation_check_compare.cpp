#include "mco/installation_check.hpp"
#include "installation_check_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        installation_check_cases::compare(input);
    });
}
