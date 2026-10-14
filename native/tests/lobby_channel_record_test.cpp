#include "mco/lobby_channel_record.hpp"

#include <algorithm>
#include <iostream>
#include <stdexcept>

int main() {
    int failures = 0;
    const auto check = [&](bool condition) { if (!condition) ++failures; };
    const auto rejects = [&](const auto& action) {
        try { action(); ++failures; } catch (const std::invalid_argument&) {}
    };
    std::array<std::uint8_t, mco::channel_argument_size> argument{};
    mco::ChannelImage allocated;
    allocated.fill(0xa5);
    argument.fill(0xc3);
    argument[0x11] = 0; // strncpy pads after a one-byte name.
    for (unsigned mask = 0; mask < 16; ++mask) {
        const unsigned flags = (mask & 1 ? 1 : 0) | (mask & 2 ? 4 : 0)
            | (mask & 4 ? 0x20 : 0) | (mask & 8 ? 0x4000 : 0);
        for (std::size_t index = 0; index < 4; ++index)
            argument[0xc + index] = static_cast<std::uint8_t>(flags >> (8 * index));
        const auto image = mco::initialize_channel_image(argument,allocated);
        check(image[0x6e] == (flags & 1 ? 1 : (flags & 4 ? 4 : 2)) && image[0x6f] == 0);
        check(image[0x6a] == (flags & 0x20) && image[0x6b] == 0);
        check(image[0x82] == 0 && image[0x83] == (flags & 0x4000 ? 0x40 : 0));
        check(image[0xc] == 0xc3 && image[0xd] == 0 && image[0x29] == 0);
        check(image[0x2a] == 0xa5 && image[0x2b] == 0xa5);
        check(std::equal(image.begin(),image.begin() + 4,allocated.begin()));
        check(std::equal(image.begin() + 0x1a0,image.end(),allocated.begin() + 0x1a0));
        const auto record = mco::materialize_channel_record(image);
        check(record[0x22] == 0xa5 && record[0x23] == 0xa5);
        check(record[0x85] == 0xa5 && record[0x8a] == 0xa5 && record[0x8b] == 0xa5);
        check(std::equal(record.begin() + 0x1a0,record.end(),argument.begin() + 0xc));
        check(std::equal(record.begin() + 0xa0,record.begin() + 0x1a0,argument.begin() + 0x50));
    }
    // No NUL in the first 30 bytes: preserve all 30 and leave tail untouched.
    std::fill(argument.begin() + 0x10,argument.begin() + 0x30,'n');
    const auto long_name = mco::initialize_channel_image(argument,allocated);
    check(std::all_of(long_name.begin() + 0xc,long_name.begin() + 0x2a,[](auto value) { return value == 'n'; }));
    check(long_name[0x2a] == 0xa5 && long_name[0x2b] == 0xa5);
    for (auto size : {std::size_t{0}, mco::channel_argument_size - 1, mco::channel_argument_size + 1}) {
        std::vector<std::uint8_t> wrong(size);
        rejects([&] { (void)mco::initialize_channel_image(wrong,allocated); });
    }
    for (auto size : {std::size_t{0}, mco::channel_allocation_size - 1, mco::channel_allocation_size + 1}) {
        std::vector<std::uint8_t> wrong(size);
        rejects([&] { (void)mco::initialize_channel_image(argument,wrong); });
        rejects([&] { (void)mco::materialize_channel_record(wrong); });
    }
    if (failures) std::cerr << failures << " channel record checks failed\n";
    return failures ? 1 : 0;
}
