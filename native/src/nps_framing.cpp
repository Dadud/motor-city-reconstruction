#include "mco/nps_framing.hpp"

#include <algorithm>
#include <stdexcept>

namespace mco {
namespace {
std::uint16_t read16(std::span<const std::uint8_t> input, std::size_t offset) {
    return static_cast<std::uint16_t>((static_cast<std::uint16_t>(input[offset]) << 8)
        | input[offset + 1]);
}
void append16(std::vector<std::uint8_t>& output, std::uint16_t value) {
    output.push_back(static_cast<std::uint8_t>(value >> 8));
    output.push_back(static_cast<std::uint8_t>(value));
}
} // namespace

std::uint16_t nps_native_flags(std::uint16_t message_id) noexcept {
    return ((message_id >= 0x501 && message_id <= 0x51a)
        || (message_id >= 0x521 && message_id <= 0x526)) ? 0x101 : 0;
}

std::vector<std::uint8_t> encode_nps_frame(const NpsFrame& frame) {
    if (frame.body.size() > nps_max_frame_bytes - 4)
        throw std::invalid_argument("NPS frame exceeds uint16 length");
    std::vector<std::uint8_t> output;
    output.reserve(4 + frame.body.size());
    append16(output, frame.message_id);
    append16(output, static_cast<std::uint16_t>(4 + frame.body.size()));
    output.insert(output.end(), frame.body.begin(), frame.body.end());
    return output;
}

std::vector<std::uint8_t> encode_nps_message(
    std::uint16_t message_id, std::span<const std::uint8_t> payload,
    std::uint32_t auxiliary) {
    if (payload.size() > nps_max_frame_bytes - 12)
        throw std::invalid_argument("NPS message exceeds uint16 length");
    NpsFrame frame{message_id, {}};
    frame.body.reserve(8 + payload.size());
    append16(frame.body, nps_native_flags(message_id));
    append16(frame.body, 0);
    for (int shift = 24; shift >= 0; shift -= 8)
        frame.body.push_back(static_cast<std::uint8_t>(auxiliary >> shift));
    frame.body.insert(frame.body.end(), payload.begin(), payload.end());
    return encode_nps_frame(frame);
}

NpsMessageHeader nps_message_header(const NpsFrame& frame) {
    if (frame.body.size() > nps_max_frame_bytes - 4)
        throw std::invalid_argument("NPS frame exceeds uint16 length");
    if (frame.body.size() < 8)
        throw std::invalid_argument("NPS frame too short for message header");
    std::uint32_t auxiliary = 0;
    for (std::size_t index = 4; index < 8; ++index)
        auxiliary = (auxiliary << 8) | frame.body[index];
    return {frame.message_id, static_cast<std::uint16_t>(4 + frame.body.size()),
            read16(frame.body, 0), read16(frame.body, 2), auxiliary};
}

std::vector<NpsFrame> NpsFrameDecoder::feed(std::span<const std::uint8_t> data) {
    if (failed_)
        throw std::invalid_argument("NPS decoder failed; discard connection");
    std::vector<NpsFrame> frames;
    std::size_t cursor = 0;
    while (cursor < data.size()) {
        const std::size_t target = pending_.size() >= 4 ? read16(pending_, 2) : 4;
        const auto count = std::min(target - pending_.size(), data.size() - cursor);
        pending_.insert(pending_.end(), data.begin() + cursor, data.begin() + cursor + count);
        cursor += count;
        if (pending_.size() < 4) continue;
        const auto length = read16(pending_, 2);
        if (length < 4) {
            pending_.clear();
            failed_ = true;
            throw std::invalid_argument("NPS frame length smaller than prefix");
        }
        if (pending_.size() == length) {
            frames.push_back({read16(pending_, 0),
                              {pending_.begin() + 4, pending_.end()}});
            pending_.clear();
        }
    }
    return frames;
}

void NpsFrameDecoder::finish() const {
    if (failed_ || !pending_.empty())
        throw std::invalid_argument("NPS connection ended with invalid or incomplete framing");
}

} // namespace mco
