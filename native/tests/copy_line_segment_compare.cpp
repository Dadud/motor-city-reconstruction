#include "mco/copy_line_segment.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto source = read(input);
        const auto destination = read(input);
        const auto limit = std::bit_cast<std::int32_t>(read(input));
        auto backing = image<192>(input);
        emit(mco::copy_line_segment(view<32>(backing, destination), view<32>(backing, source), limit));
        emit(backing);
    });
}
