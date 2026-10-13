#pragma once

#include <cstdint>
#include <span>
#include <string>
#include <vector>

namespace mco {
struct VivEntry {
    // Archive Latin-1 name decoded to UTF-8. Names are identifiers, not paths
    // validated for extraction; callers must apply separate path containment.
    std::string name;
    std::uint32_t offset;
    std::uint32_t size;
};

// Validates BIGF/BIG4 header, directory and nonoverlapping payload bounds.
// Preserves on-disk entry order. Returned entries do not retain the input span.
std::vector<VivEntry> parse_viv_directory(std::span<const std::uint8_t> archive);
} // namespace mco
