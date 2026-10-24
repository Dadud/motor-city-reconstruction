#include "mco/string_compare.hpp"
#include <algorithm>
#include <stdexcept>

namespace mco {
namespace {
std::uint8_t fold(std::uint8_t value) {
  const auto wrapped = static_cast<std::uint8_t>(value + 0xbfu);
  return static_cast<std::uint8_t>(wrapped + (wrapped < 0x1a ? 0x20u : 0u) + 0x41u);
}
}

int compare_config_names(std::span<const std::byte> left,
                         std::span<const std::byte> right) {
  const auto left_end = std::find(left.begin(), left.end(), std::byte{0});
  const auto right_end = std::find(right.begin(), right.end(), std::byte{0});
  if (left_end == left.end() || right_end == right.end())
    throw std::invalid_argument("NUL-terminated byte spans required");
  std::size_t index = 0;
  for (;;) {
    const auto first = std::to_integer<std::uint8_t>(left[index]);
    const auto second = std::to_integer<std::uint8_t>(right[index]);
    if (first == second) {
      if (first == 0) return 0;
      ++index;
      continue;
    }
    const auto first_folded = fold(first);
    const auto second_folded = fold(second);
    if (first_folded != second_folded)
      return first_folded < second_folded ? -1 : 1;
    ++index;
  }
}
}
