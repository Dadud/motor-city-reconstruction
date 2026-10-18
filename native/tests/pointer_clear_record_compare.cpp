#include "mco/pointer_clear_record.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto pointer = read(input);
        auto record = read(input);
        auto target = image<8>(input);
        mco::pointer_clear_record(pointer ? std::span<std::byte>(target.data(),4) : std::span<std::byte>{}, pointer, record);
        emit(record);
        emit(target);
    });
}
