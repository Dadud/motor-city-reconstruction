#include "mco/primary_value_store.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        auto destination = read(input);
        const auto value = read(input);
        mco::primary_value_store(destination, value);
        emit(destination);
    });
}
