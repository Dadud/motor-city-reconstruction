#include "mco/buffer_copy12_b.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        auto destination = image<24>(input);
        const auto source = image<12>(input);
        mco::buffer_copy12_b(std::span<std::byte,12>(destination.data()+8,12), source);
        emit(destination);
        emit(source);
    });
}
