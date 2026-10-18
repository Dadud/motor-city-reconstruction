#include "mco/free_camera_update.hpp"
#include "free_camera_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        free_camera_cases::compare(input);
    });
}
