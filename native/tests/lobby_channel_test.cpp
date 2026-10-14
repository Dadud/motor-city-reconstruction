#include "mco/lobby_channel_codec.hpp"
#include <array>
#include <algorithm>
#include <iostream>
#include <stdexcept>

int main() {
    int failures = 0;
    const auto check = [&](bool value) { if (!value) ++failures; };
    const auto rejects = [&](const auto& action) {
        try { action(); ++failures; } catch (const std::invalid_argument&) {}
    };
    std::array<std::uint8_t, mco::channel_record_size> raw{};
    auto output = mco::encode_channel_join_payload(raw);
    check(output.size() == 321 && output[7] == 1);
    for (std::size_t i = 0; i < 256; ++i) raw[0xa0 + i] = static_cast<std::uint8_t>(i);
    output = mco::encode_channel_join_payload(raw);
    check(std::equal(raw.begin() + 0xa0, raw.begin() + 0x1a0, output.end() - 260));
    std::fill(raw.begin() + 4, raw.begin() + 35, 'n');
    std::fill(raw.begin() + 0x74, raw.begin() + 0x85, 't');
    rejects([&] { (void)mco::encode_channel_join_payload(raw); });
    raw[34] = 0;
    check(mco::encode_channel_join_payload(raw).size() == 368);
    raw[35] = 'n'; raw[34] = 'n';
    rejects([&] { (void)mco::encode_channel_join_payload(raw); });
    rejects([&] { (void)mco::encode_channel_join_payload({}); });
    const std::array<std::uint8_t, 8> reply{0x12,0x34,0x56,0x78,0xff,0xff,0xff,0xff};
    for (auto id : {0x214, 0x215}) {
        const auto decoded = mco::decode_channel_join_success(id, reply);
        check(decoded.channel_id == 0x12345678 && decoded.value_2 == 0xffffffff);
    }
    rejects([&] { (void)mco::decode_channel_join_success(0x213, reply); });
    for (std::size_t i = 0; i < 8; ++i)
        rejects([&] { (void)mco::decode_channel_join_success(0x214, std::span(reply).first(i)); });
    if (failures) std::cerr << failures << " channel codec checks failed\n";
    return failures ? 1 : 0;
}
