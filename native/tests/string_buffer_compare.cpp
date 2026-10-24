#include "cell_io.hpp"
#include "mco/string_buffer.hpp"

int main() {
  return cell_io::run([](std::istream &input) {
    using namespace cell_io;
    const auto length = read(input), capacity = read(input);
    auto memory = image<80>(input);
    const auto source_offset = read(input), destination_offset = read(input);
    auto destination = view<33>(memory, destination_offset);
    const auto source = std::span<const std::byte, 33>(memory.data() + source_offset, 33);
    emit(mco::assign_inline_buffer(destination, source, length, capacity));
    emit(memory);
  });
}
