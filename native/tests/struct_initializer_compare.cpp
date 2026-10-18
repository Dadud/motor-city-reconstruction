#include "mco/struct_initializer.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        auto count = image<8>(input);
        auto state = image<16>(input);
        mco::struct_initializer(std::span<std::byte,4>(count.data(),4), std::span<std::byte,12>(state.data(),12));
        emit(count);
        emit(state);
    });
}
