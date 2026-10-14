#include "mco/game_start_flow.hpp"
#include <iostream>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <limits>

namespace {
std::string hex(std::span<const std::uint8_t> bytes) {
    std::ostringstream out;
    for (auto byte : bytes) out << std::hex << std::setw(2) << std::setfill('0') << unsigned(byte);
    return out.str();
}
template<class T> std::string value(std::optional<T> input) { return input ? std::to_string(*input) : "-"; }
void emit(const mco::GameStartFlow& flow) {
    const auto action = flow.action();
    std::cout << static_cast<unsigned>(action.kind) << ' ' << value(action.owner_offset) << ' '
              << value(action.operation_id) << ' ' << value(action.channel_id) << ' '
              << value(action.result) << ' ' << (action.argument ? hex(*action.argument) : "-")
              << ' ' << hex(flow.network_image()) << '\n';
}
void write(std::vector<std::uint8_t>& image, std::size_t offset, std::uint32_t value) {
    for (unsigned i = 0; i < 4; ++i) image[offset + i] = static_cast<std::uint8_t>(value >> (8*i));
}
std::uint32_t u32(std::uint64_t value) {
    if (value > 0xffffffffu) throw std::invalid_argument("wide uint32 input");
    return static_cast<std::uint32_t>(value);
}
std::int32_t i32(std::int64_t value) {
    if (value < std::numeric_limits<std::int32_t>::min() || value > std::numeric_limits<std::int32_t>::max())
        throw std::invalid_argument("wide int32 input");
    return static_cast<std::int32_t>(value);
}
}
int main() {
    try {
        std::uint64_t selector, channel;
        if (!(std::cin >> selector >> channel)) return 2;
        std::vector<std::uint8_t> image(0x600, 0xa5);
        write(image, 0x5cc, u32(selector)); write(image, 0x160, u32(channel));
        mco::GameStartFlow flow(image); emit(flow);
        char event; unsigned count = 0;
        while (std::cin >> event) {
            if (++count > 100) return 2;
            std::int64_t result; std::uint64_t id, new_channel; unsigned present;
            if (event == 'e' && (std::cin >> id)) flow.enqueued(u32(id));
            else if (event == 'q' && (std::cin >> present >> result) && present <= 1)
                flow.completion_queried(present ? std::optional{i32(result)} : std::nullopt);
            else if (event == 'p' && (std::cin >> result >> new_channel)) {
                auto observed = std::vector<std::uint8_t>(flow.network_image().begin(), flow.network_image().end());
                write(observed, 0x160, u32(new_channel)); flow.application_pumped(i32(result), observed);
            } else if (event == 's' && (std::cin >> present >> id) && present <= 1)
                flow.room_status_queried(present ? std::optional{u32(id)} : std::nullopt);
            else return 2;
            emit(flow);
        }
        return 0;
    } catch (const std::exception&) { return 1; }
}
