#include "mco/lobby_channel_codec.hpp"
#include <algorithm>
#include <stdexcept>

namespace mco {
std::vector<std::uint8_t> encode_channel_join_payload(std::span<const std::uint8_t> raw) {
    if (raw.size() != channel_record_size) throw std::invalid_argument("invalid channel record size");
    std::vector<std::uint8_t> output;
    output.reserve(channel_payload_limit);
    const auto integer = [&](std::size_t offset, std::size_t width) {
        for (std::size_t i = width; i > 0; --i) output.push_back(raw[offset + i - 1]);
    };
    const auto string = [&](std::size_t start, std::size_t end) {
        const auto text = raw.subspan(start, end - start);
        const auto terminator = std::find(text.begin(), text.end(), 0);
        if (terminator == text.end()) throw std::invalid_argument("unterminated channel string");
        const auto count = static_cast<std::uint32_t>(terminator - text.begin() + 1);
        for (int shift = 24; shift >= 0; shift -= 8)
            output.push_back(static_cast<std::uint8_t>(count >> shift));
        output.insert(output.end(), text.begin(), terminator + 1);
    };
    integer(0, 4);
    string(4, 0x24);
    for (auto offset : {0x24, 0x28, 0x50, 0x54, 0x58}) integer(offset, 4);
    for (auto offset : {0x5c, 0x5e, 0x60, 0x62, 0x64, 0x66}) integer(offset, 2);
    string(0x74, 0x86);
    integer(0x86, 2);
    output.push_back(raw[0x88]);
    for (auto offset : {0x8a, 0x8c}) integer(offset, 2);
    for (auto offset : {0x90, 0x94}) integer(offset, 4);
    output.insert(output.end(), raw.begin() + 0xa0, raw.begin() + 0x1a0);
    integer(0x1a0, 4);
    if (output.size() > channel_payload_limit) throw std::invalid_argument("channel payload exceeds capacity");
    return output;
}
ChannelJoinSuccess decode_channel_join_success(std::uint16_t id, std::span<const std::uint8_t> body) {
    if ((id != 0x214 && id != 0x215) || body.size() != 8)
        throw std::invalid_argument("invalid channel success reply");
    const auto integer = [&](std::size_t start) {
        std::uint32_t value = 0;
        for (std::size_t i = start; i < start + 4; ++i) value = (value << 8) | body[i];
        return value;
    };
    return {id, integer(0), integer(4)};
}
}
