#include "mco/window_procedure.hpp"
#include "window_dispatch_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        window_dispatch_cases::compare(input,true);
    });
}
