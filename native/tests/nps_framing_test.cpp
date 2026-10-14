#include "mco/nps_framing.hpp"

#include <algorithm>
#include <array>
#include <iostream>
#include <stdexcept>

int main() {
    int failures = 0;
    const auto check = [&](bool value) { if (!value) ++failures; };
    const auto rejects = [&](const auto& action) {
        try { action(); ++failures; } catch (const std::invalid_argument&) {}
    };
    const std::array<std::uint8_t, 2> payload{0, 0xff};
    const std::vector<std::uint8_t> expected{5,1,0,14,1,1,0,0,0x12,0x34,0x56,0x78,0,0xff};
    check(mco::encode_nps_message(0x501, payload, 0x12345678) == expected);
    mco::NpsFrameDecoder initial;
    const auto decoded = initial.feed(expected);
    check(decoded.size() == 1);
    check(mco::nps_message_header(decoded[0]) == mco::NpsMessageHeader{0x501,14,0x101,0,0x12345678});
    initial.finish();
    // Exhaust all IDs, including both flag-range boundaries.
    for (unsigned id = 0; id <= 65535; ++id)
        check(mco::nps_native_flags(static_cast<std::uint16_t>(id)) ==
              ((id >= 0x501 && id <= 0x51a) || (id >= 0x521 && id <= 0x526) ? 0x101 : 0));
    const std::vector<mco::NpsFrame> frames{{0xffff,{0,0xff}}, {1,{}}, {0x601,{'a','b','c'}}};
    std::vector<std::uint8_t> stream;
    for (const auto& frame : frames) {
        const auto wire = mco::encode_nps_frame(frame);
        stream.insert(stream.end(), wire.begin(), wire.end());
    }
    for (std::size_t split = 0; split <= stream.size(); ++split) {
        mco::NpsFrameDecoder decoder;
        auto actual = decoder.feed(std::span(stream).first(split));
        const auto rest = decoder.feed(std::span(stream).subspan(split));
        actual.insert(actual.end(), rest.begin(), rest.end());
        check(actual == frames);
        decoder.finish();
    }
    mco::NpsFrame maximum{0xffff, std::vector<std::uint8_t>(65531,0xa5)};
    const auto wire = mco::encode_nps_frame(maximum);
    check(wire.size() == 65535 && wire[2] == 0xff && wire[3] == 0xff);
    mco::NpsFrameDecoder single_byte;
    std::vector<mco::NpsFrame> gathered;
    for (const auto& byte : wire) {
        auto part = single_byte.feed(std::span(&byte, 1));
        gathered.insert(gathered.end(), part.begin(), part.end());
    }
    check(gathered == std::vector<mco::NpsFrame>{maximum});
    single_byte.finish();
    maximum.body.push_back(0);
    rejects([&] { (void)mco::encode_nps_frame(maximum); });
    rejects([&] { (void)mco::nps_message_header(maximum); });
    check(mco::encode_nps_message(0x601, std::vector<std::uint8_t>(65523), 0xffffffff).size() == 65535);
    rejects([&] { (void)mco::encode_nps_message(1, std::vector<std::uint8_t>(65524)); });
    for (std::size_t size = 0; size < 8; ++size)
        rejects([&] { (void)mco::nps_message_header({1,std::vector<std::uint8_t>(size)}); });
    for (std::uint8_t length = 0; length < 4; ++length) {
        mco::NpsFrameDecoder bad;
        const std::array<std::uint8_t,4> prefix{0,1,0,length};
        rejects([&] { (void)bad.feed(prefix); });
        rejects([&] { (void)bad.feed({}); });
        rejects([&] { bad.finish(); });
    }
    // Every truncated position of a header-enabled frame must fail at EOF.
    for (std::size_t cut = 1; cut < expected.size(); ++cut) {
        mco::NpsFrameDecoder truncated;
        (void)truncated.feed(std::span(expected).first(cut));
        rejects([&] { truncated.finish(); });
    }
    // Received flags/reserved are retained, never normalized to serializer values.
    const auto header = mco::nps_message_header({0x601,{0xff,0xff,0xab,0xcd,0xff,0xff,0xff,0xff}});
    check(header.flags == 65535 && header.reserved == 0xabcd && header.auxiliary == 0xffffffff);
    if (failures) std::cerr << failures << " NPS framing checks failed\n";
    return failures ? 1 : 0;
}
