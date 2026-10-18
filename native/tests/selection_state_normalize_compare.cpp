#include "mco/selection_state_normalize.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        auto state = image<24>(input);
        emit(mco::selection_state_normalize(state));
        emit(state);
    });
}
