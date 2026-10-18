#include "mco/registry_slot_write.hpp"
#include <span>
#include <stdexcept>
int main() {
    std::array<std::byte, 0x1804> registry{};
    registry.fill(std::byte{0});
    mco::registry_slot_write(registry, 7, 0x11111111, 0x22222222, 0x33333333);
    auto word = [&registry](size_t offset) {
        return static_cast<std::uint32_t>(registry[offset])
            | static_cast<std::uint32_t>(registry[offset+1]) << 8
            | static_cast<std::uint32_t>(registry[offset+2]) << 16
            | static_cast<std::uint32_t>(registry[offset+3]) << 24; };
    const size_t base = 7*24;
    if (word(base+12) != 0x11111111 || word(base+16) != 0x22222222
            || word(base+20) != 0x33333333)
        throw std::runtime_error("slot fields must land at 12/16/20");
    if (word(base) != 0)
        throw std::runtime_error("the slot head field is not written here");
    try { mco::registry_slot_write(registry, 256, 1, 1, 1); }
    catch (const std::invalid_argument&) { return 0; }
    throw std::runtime_error("slot past the table must be rejected");
}
