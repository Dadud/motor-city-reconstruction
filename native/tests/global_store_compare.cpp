#include "mco/global_store.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto stored = read(input);
        const auto returned = read(input);
        auto destination = image<4>(input);
        emit(mco::global_store(destination, stored, returned));
        emit(destination);
    });
}
