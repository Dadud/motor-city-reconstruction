#include "mco/startup_thread_runtime.hpp"
#include "startup_thread_runtime_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        startup_thread_runtime_cases::compare(input);
    });
}
