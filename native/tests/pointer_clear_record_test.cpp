#include "mco/pointer_clear_record.hpp"
#include <array>
#include <stdexcept>
int main() {
    std::array<std::byte,4> target{};
    target.fill(static_cast<std::byte>(0x77));
    std::uint32_t record = 0xdeadbeefu;
    mco::pointer_clear_record(target, 0x00f0f0f0u, record);
    for (unsigned k = 0; k < 4; ++k)
        if (target[k] != std::byte{0})
            throw std::runtime_error("the pointer target must clear");
    if (record != 0x00f0f0f0u)
        throw std::runtime_error("the record global must take the pointer");
    mco::pointer_clear_record({}, 0, record);
    if (record != 0x00f0f0f0u)
        throw std::runtime_error("a null pointer must preserve the record");
    return 0;
}
