#include "mco/registry_register.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto counter = read(input);
        const auto head = read(input);
        auto node = image<0x5c>(input);
        emit(mco::registry_register(std::span<std::byte,0x58>(node.data(),0x58), counter, head));
        emit(node);
    });
}
