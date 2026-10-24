#include "cell_io.hpp"
#include "mco/string_buffer.hpp"
#include <array>
#include <span>

int main() {
  return cell_io::run([](std::istream& input) {
    using namespace cell_io;
    const auto length = read(input), capacity = read(input), old_length = read(input);
    const auto header = read(input), source_offset = read(input);
    auto memory = image<160>(input);
    std::array<std::byte, 128> fresh{};
    std::uint32_t allocation_size = 0, releases = 0;
    mco::BufferRecord record{{}, old_length, capacity};
    if (header != 256) {
      auto storage = view<1>(memory, 0);
      storage[0] = std::byte(header);
      record.storage = std::span<std::byte>(memory.data(), capacity + 2);
    }
    const auto source = std::span<const std::byte>(memory.data() + source_offset, length);
    const auto result = mco::assign_buffer(
        record, source, length,
        [&](std::uint32_t size) {
          allocation_size = size;
          return std::span<std::byte>(fresh.data(), size);
        },
        [&](std::span<std::byte>) { ++releases; });
    emit(result);
    emit(record.length);
    emit(record.capacity);
    emit(releases);
    emit(allocation_size);
    emit(memory);
    emit(fresh);
  });
}
