#include "mco/room_server_binding.hpp"

#include <bit>
#include <limits>
#include <stdexcept>

namespace {
void check(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
void put(std::vector<std::uint8_t>& image, std::size_t offset, std::uint32_t value) {
    for (std::size_t i = 0; i < 4; ++i) image[offset + i] = static_cast<std::uint8_t>(value >> (8 * i));
}
} // namespace

int main() {
    std::vector<std::uint8_t> source(mco::network_owner_min_size + 23);
    for (std::size_t i = 0; i < source.size(); ++i) source[i] = static_cast<std::uint8_t>(i * 37 + 19);
    put(source, 0x43c, 44); put(source, 0x5fc, 0xaaaaaaaau); put(source, 0x5f4, 0xfffffffau);
    const auto original = source;
    for (const auto result : {0,1,7,44,std::numeric_limits<std::int32_t>::max()}) {
        const auto output = mco::apply_server_connection_result(source, result);
        auto expected = source;
        const auto bits = std::bit_cast<std::uint32_t>(result);
        put(expected, 0x5cc, bits); put(expected, 0x43c, bits); put(expected, 0x5fc, 1); put(expected, 0x600, 0);
        check(output.owner_image == expected, "success image writes or preserved error mismatch");
        check(output.return_code == result && output.mini_room_list_requested && output.notification &&
              *output.notification == std::array<std::int32_t, 2>{result, 0}, "success helper intents mismatch");
    }
    for (const auto result : {-1,-6,-51,-59,std::numeric_limits<std::int32_t>::min()}) {
        const auto output = mco::apply_server_connection_result(source, result);
        auto expected = source;
        const auto bits = std::bit_cast<std::uint32_t>(result);
        put(expected, 0x5cc, bits); put(expected, 0x5f4, bits); put(expected, 0x600, 0);
        check(output.owner_image == expected, "failure selector/connected preservation or signed writes mismatch");
        check(output.return_code == result && !output.mini_room_list_requested && !output.notification,
              "failure helper intents mismatch");
    }
    check(source == original, "input owner image modified");
    bool rejected = false;
    try { mco::apply_server_connection_result(std::span<const std::uint8_t>{source}.first(mco::network_owner_min_size - 1), 0); }
    catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "incomplete owner image accepted");
    check(mco::apply_server_connection_result(std::span<const std::uint8_t>{source}.first(mco::network_owner_min_size), 0).owner_image.size()
          == mco::network_owner_min_size, "exact minimum image rejected");
}
