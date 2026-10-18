#include "mco/record_state_copy48.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto record = read(input);
        const auto destination = read(input);
        auto backing = image<512>(input);
        mco::record_state_copy48(view<48>(backing, destination), view<256>(backing, record));
        emit(backing);
    });
}
