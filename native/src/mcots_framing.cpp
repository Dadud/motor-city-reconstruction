#include "mco/mcots_framing.hpp"

#include <stdexcept>

namespace mco {
namespace {

void write_little(std::vector<std::uint8_t>& output, std::size_t offset,
                  std::uint32_t value, std::size_t count) {
    for (std::size_t index = 0; index < count; ++index)
        output[offset + index] = static_cast<std::uint8_t>(value >> (8 * index));
}

std::uint32_t read_little(std::span<const std::uint8_t> input,
                          std::size_t offset, std::size_t count) {
    std::uint32_t value = 0;
    for (std::size_t index = 0; index < count; ++index)
        value |= static_cast<std::uint32_t>(input[offset + index]) << (8 * index);
    return value;
}

} // namespace

std::vector<std::uint8_t> encode_mcots_frame(
    McotsHeader header, std::span<const std::uint8_t> payload) {
    if (payload.empty() || payload.size() > mcots_maximum_payload)
        throw std::invalid_argument("MCOTS payload must contain 1..65526 bytes");
    std::vector<std::uint8_t> output(mcots_header_size + payload.size());
    write_little(output, 0, static_cast<std::uint32_t>(payload.size() + 9), 2);
    write_little(output, 2, mcots_marker, 4);
    write_little(output, 6, header.transaction_value, 4);
    output[10] = header.flags;
    for (std::size_t index = 0; index < payload.size(); ++index)
        output[mcots_header_size + index] = payload[index];
    return output;
}

McotsFrame decode_mcots_frame(std::span<const std::uint8_t> wire) {
    if (wire.size() < mcots_header_size + 1)
        throw std::invalid_argument("truncated MCOTS frame");
    const auto length = read_little(wire, 0, 2);
    if (length + 2 != wire.size() || read_little(wire, 2, 4) != mcots_marker)
        throw std::invalid_argument("invalid MCOTS frame length or marker");
    return {{read_little(wire, 6, 4), wire[10]},
            {wire.begin() + mcots_header_size, wire.end()}};
}

} // namespace mco
