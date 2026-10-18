#include "mco/scratch_clear_return.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto present = read(input);
        const auto primary = read(input);
        auto target = image<8>(input);
        emit(mco::clear_through(present ? std::span<std::byte>(target.data(),4) : std::span<std::byte>{}, primary));
        emit(target);
    });
}
