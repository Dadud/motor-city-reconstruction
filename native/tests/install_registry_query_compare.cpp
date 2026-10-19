#include "mco/install_registry_query.hpp"
#include "install_registry_query_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        install_registry_query_cases::compare(input);
    });
}
