#include "mco/mcots_framing.hpp"

#include <algorithm>
#include <array>
#include <iostream>
#include <stdexcept>
#include <vector>

int main() {
    int failures = 0;
    const auto require = [&](bool condition, const char* message) {
        if (!condition) { std::cerr << message << '\n'; ++failures; }
    };
    const auto rejects = [&](const auto& action, const char* message) {
        try { action(); require(false, message); }
        catch (const std::invalid_argument&) {}
    };

    const mco::McotsHeader header{0x12345678, 0};
    const std::vector<std::uint8_t> login_sized_payload(39, 0);
    const auto wire = mco::encode_mcots_frame(header, login_sized_payload);
    const std::array<std::uint8_t, 11> expected{
        0x30, 0x00, 0x54, 0x4f, 0x4d, 0x43, 0x78, 0x56, 0x34, 0x12, 0x00};
    require(wire.size() == 50 && std::equal(expected.begin(), expected.end(), wire.begin()),
            "native sender envelope bytes must match");
    const auto decoded = mco::decode_mcots_frame(wire);
    require(decoded.header == header && decoded.payload == login_sized_payload,
            "payload and immutable header must round trip");

    const std::array<std::uint8_t, 1> one{0xff};
    for (unsigned flag = 0; flag <= 255; ++flag) {
        const mco::McotsHeader opaque{0xffffffff, static_cast<std::uint8_t>(flag)};
        const auto result = mco::decode_mcots_frame(mco::encode_mcots_frame(opaque, one));
        require(result.header == opaque && result.payload[0] == 0xff,
                "all flags and transaction bits must be preserved without transforms");
    }
    const std::vector<std::uint8_t> maximum(mco::mcots_maximum_payload, 0x78);
    const auto maximum_wire = mco::encode_mcots_frame({0, 255}, maximum);
    require(maximum_wire[0] == 0xff && maximum_wire[1] == 0xff &&
                mco::decode_mcots_frame(maximum_wire).payload == maximum,
            "maximum payload must use full uint16 length");
    rejects([&] { (void)mco::encode_mcots_frame({0, 0}, {}); }, "empty payload accepted");
    const std::vector<std::uint8_t> oversized(mco::mcots_maximum_payload + 1);
    rejects([&] { (void)mco::encode_mcots_frame({0, 0}, oversized); }, "oversized payload accepted");
    for (std::size_t length = 0; length < wire.size(); ++length)
        rejects([&] { (void)mco::decode_mcots_frame(std::span(wire).first(length)); },
                "truncated frame accepted");
    auto corrupt = wire;
    corrupt[2] ^= 0xff;
    rejects([&] { (void)mco::decode_mcots_frame(corrupt); }, "bad marker accepted");
    corrupt = wire;
    corrupt[0] -= 1;
    rejects([&] { (void)mco::decode_mcots_frame(corrupt); }, "bad length accepted");
    corrupt = wire;
    corrupt.insert(corrupt.end(), wire.begin(), wire.end());
    rejects([&] { (void)mco::decode_mcots_frame(corrupt); }, "additional frame accepted");
    return failures == 0 ? 0 : 1;
}
