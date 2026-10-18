#include "mco/entity_or_store.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto value = read(input);
        auto target = image<0x9c>(input);
        mco::entity_or_store(target, value);
        emit(target);
    });
}
