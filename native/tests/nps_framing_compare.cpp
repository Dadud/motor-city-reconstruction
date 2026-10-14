#include "mco/nps_framing.hpp"

#include <algorithm>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string_view>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

// Private comparison protocol, never transmitted to a game service.
// frame: BE uint16 ID + body; message: BE uint16 ID + uint32 auxiliary + payload;
// stream: BE uint16 chunk size + plain frame stream; header: one encoded frame.
// Success prints bytes; codec rejection exits 1; invalid runner input exits 2.
int main(int argc, char** argv) {
#ifdef _WIN32
    _setmode(_fileno(stdin), _O_BINARY);
    _setmode(_fileno(stdout), _O_BINARY);
#endif
    if (argc != 2) return 2;
    std::vector<std::uint8_t> input;
    // Explicit harness bound, above the largest corpus multi-frame stream.
    for (char byte; std::cin.get(byte); ) {
        if (input.size() == 2 * 1024 * 1024) return 2;
        input.push_back(static_cast<std::uint8_t>(byte));
    }
    const std::string_view mode(argv[1]);
    std::vector<std::uint8_t> output;
    const auto read16 = [&](std::size_t offset) {
        return static_cast<std::uint16_t>((input[offset] << 8) | input[offset + 1]);
    };
    try {
        if (mode == "frame") {
            if (input.size() < 2) return 2;
            output = mco::encode_nps_frame({read16(0),{input.begin() + 2,input.end()}});
        } else if (mode == "message") {
            if (input.size() < 6) return 2;
            std::uint32_t auxiliary = 0;
            for (std::size_t i = 2; i < 6; ++i) auxiliary = (auxiliary << 8) | input[i];
            output = mco::encode_nps_message(read16(0), std::span(input).subspan(6), auxiliary);
        } else if (mode == "stream" || mode == "header") {
            std::size_t offset = 0, chunk = input.size() ? input.size() : 1;
            if (mode == "stream") {
                if (input.size() < 2 || read16(0) == 0) return 2;
                offset = 2;
                chunk = read16(0);
            }
            mco::NpsFrameDecoder decoder;
            std::vector<mco::NpsFrame> frames;
            while (offset < input.size()) {
                const auto count = std::min(chunk, input.size() - offset);
                auto decoded = decoder.feed(std::span(input).subspan(offset,count));
                frames.insert(frames.end(), decoded.begin(), decoded.end());
                offset += count;
            }
            decoder.finish();
            if (mode == "header") {
                if (frames.size() != 1) return 2;
                (void)mco::nps_message_header(frames[0]);
                const auto wire = mco::encode_nps_frame(frames[0]);
                output.assign(wire.begin(), wire.begin() + 12);
            } else {
                for (const auto& frame : frames) {
                    const auto wire = mco::encode_nps_frame(frame);
                    output.insert(output.end(), wire.begin(), wire.end());
                }
            }
        } else return 2;
    } catch (const std::invalid_argument&) {
        return 1;
    }
    std::cout.write(reinterpret_cast<const char*>(output.data()), static_cast<std::streamsize>(output.size()));
    return std::cout ? 0 : 2;
}
