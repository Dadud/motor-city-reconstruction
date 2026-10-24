#include "cell_io.hpp"
#include "mco/string_compare.hpp"
#include <span>

int main() {
  return cell_io::run([](std::istream& input) {
    using namespace cell_io;
    const auto left_length = read(input), right_length = read(input);
    auto memory = image<1024>(input);
    if (left_length == 0 || left_length > 512 || right_length == 0 || right_length > 512)
      throw std::invalid_argument("invalid string span length");
    const auto left = std::span<const std::byte>(memory.data(), left_length);
    const auto right = std::span<const std::byte>(memory.data() + 512, right_length);
    emit(static_cast<std::uint32_t>(mco::compare_config_names(left, right)));
  });
}
