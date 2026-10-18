#include "mco/detail/wide_int.hpp"
#include "cell_io.hpp"
#include <bit>

int main() {
    return cell_io::run([](std::istream& input) {
        using mco::detail::wide_int;
        const auto mode = cell_io::read(input);
        std::array<std::uint32_t,4> a{}, b{};
        for (auto& word : a) word = cell_io::read(input);
        for (auto& word : b) word = cell_io::read(input);
        const auto shift = cell_io::read(input);
        const auto left = wide_int::from_words(a), right = wide_int::from_words(b);
        wide_int result;
        switch (mode) {
        case 0: result = left+right; break;
        case 1: result = left-right; break;
        case 2: result = left*right; break;
        case 3: result = left&right; break;
        case 4: result = left<<shift; break;
        case 5: result = left>>shift; break;
        case 6: result = -left; break;
        case 7: {
            const auto bits = std::bit_cast<std::uint64_t>(static_cast<double>(left));
            cell_io::emit(static_cast<std::uint32_t>(bits));
            cell_io::emit(static_cast<std::uint32_t>(bits >> 32));
            return;
        }
        default: throw std::invalid_argument("unknown wide integer operation");
        }
        cell_io::emit(result.words());
    });
}
