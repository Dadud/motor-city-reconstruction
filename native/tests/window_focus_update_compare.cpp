#include "mco/window_focus_update.hpp"
#include "window_focus_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        window_focus_cases::compare(input);
    });
}
