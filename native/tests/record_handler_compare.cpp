#include "mco/record_handler.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto identifier = read(input);
        emit(mco::record_handler(identifier));
    });
}
