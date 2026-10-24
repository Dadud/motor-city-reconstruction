#pragma once
#include <cstddef>
#include <cstdint>
#include <span>

namespace mco {
// Original 0x6aa840, global locale-mode flag disabled (the INI default mode).
int compare_config_names(std::span<const std::byte> left,
                         std::span<const std::byte> right);
}
