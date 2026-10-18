#include "mco/record_pair_match.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto first = read(input);
        const auto second = read(input);
        const auto pairs = image<64>(input);
        emit(mco::record_pair_match(pairs, first, second));
        emit(pairs);
    });
}
