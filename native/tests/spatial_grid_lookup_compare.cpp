#include "mco/spatial_grid_lookup.hpp"
#include "spatial_grid_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        spatial_grid_cases::compare(input);
    });
}
