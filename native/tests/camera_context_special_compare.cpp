#include "mco/camera_context_special.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        auto context = image<12>(input);
        emit(mco::camera_context_special(context));
        emit(context);
    });
}
