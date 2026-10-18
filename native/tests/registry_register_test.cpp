#include "mco/registry_register.hpp"
#include <array>
#include <stdexcept>

int main() {
    std::array<std::byte,0x58> node{};
    for (auto& b : node) b = static_cast<std::byte>(0xcc);
    if (mco::registry_register(node, 0, 0x1234) != 1)
        throw std::runtime_error("counter must return incremented");
    auto word = [&node](size_t offset) {
        return static_cast<std::uint32_t>(node[offset])
            | static_cast<std::uint32_t>(node[offset+1]) << 8
            | static_cast<std::uint32_t>(node[offset+2]) << 16
            | static_cast<std::uint32_t>(node[offset+3]) << 24; };
    if (word(0x20) != 0)
        throw std::runtime_error("node id must take the counter");
    if (word(0x54) != 0x1234)
        throw std::runtime_error("node must link to the head");
    if (mco::registry_register(node, 0xffffffff, 0) != 0)
        throw std::runtime_error("counter wrap must be preserved");
    if (word(0x20) != 0xffffffff)
        throw std::runtime_error("wrapped id must be stored");
    return 0;
}
