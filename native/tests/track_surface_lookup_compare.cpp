#include "mco/track_surface_lookup.hpp"
#include "track_surface_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        track_surface_cases::compare(input);
    });
}
