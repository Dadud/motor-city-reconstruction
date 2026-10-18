#include "mco/copy_words24.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto source = read(input);
        const auto destination = read(input);
        auto backing = image<192>(input);
        const auto returned = mco::copy_words24(view<24>(backing, destination), view<24>(backing, source));
        emit(returned.data() == backing.data()+destination ? destination : 0xffffffffu);
        emit(backing);
    });
}
