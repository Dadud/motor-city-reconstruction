#include "mco/copy_prefix2.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto source = read(input);
        const auto destination = read(input);
        auto backing = image<96>(input);
        mco::copy_prefix2(view<3>(backing, destination), view<2>(backing, source));
        emit(backing);
    });
}
