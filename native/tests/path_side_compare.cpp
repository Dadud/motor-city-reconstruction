#include "mco/path_side.hpp"
#include "track_path_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        path_cases::compare(input,1);
    });
}
