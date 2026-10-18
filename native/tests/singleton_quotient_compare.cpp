#include "mco/singleton_quotient.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto dividend = std::bit_cast<std::int32_t>(read(input));
        const auto primary = read(input);
        const auto fallback = read(input);
        emit(std::bit_cast<std::uint32_t>(mco::singleton_quotient(dividend, primary, fallback)));
    });
}
