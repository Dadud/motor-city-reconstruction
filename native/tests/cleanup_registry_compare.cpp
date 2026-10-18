#include "mco/cleanup_registry.hpp"
#include "cleanup_registry_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        cleanup_registry_cases::compare(input);
    });
}
