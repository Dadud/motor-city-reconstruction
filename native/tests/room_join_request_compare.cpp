#include "mco/room_join_request.hpp"

#include <iostream>
#include <stdexcept>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

// Private corpus input: room image(0x3b8), flag/wait/owner-present bytes,
// uint32 LE owner token, uint8 password length, password bytes.
// 0 success; 1 codec rejection; 2 malformed harness input. No host pointers run.
int main() {
#ifdef _WIN32
    _setmode(_fileno(stdin),_O_BINARY);
    _setmode(_fileno(stdout),_O_BINARY);
#endif
    std::array<std::uint8_t,0x3c0> input;
    std::cin.read(reinterpret_cast<char*>(input.data()),input.size());
    if (std::cin.gcount() != static_cast<std::streamsize>(input.size())) return 2;
    if (input[0x3b8] > 1 || input[0x3b9] > 1 || input[0x3ba] > 1) return 2;
    std::vector<std::uint8_t> password(input[0x3bf]);
    std::cin.read(reinterpret_cast<char*>(password.data()),password.size());
    if (std::cin.gcount() != static_cast<std::streamsize>(password.size())
        || std::cin.peek() != std::char_traits<char>::eof()) return 2;
    std::uint32_t token = 0;
    for (std::size_t i = 0; i < 4; ++i) token |= static_cast<std::uint32_t>(input[0x3bb + i]) << (8 * i);
    try {
        const auto fields = mco::room_join_inputs_from_image(std::span(input).first(0x3b8));
        const auto argument = mco::build_room_join_argument(fields,password,input[0x3b8] != 0,
            input[0x3b9] != 0,input[0x3ba] ? std::optional(token) : std::nullopt);
        std::cout.write(reinterpret_cast<const char*>(argument.data()),argument.size());
    } catch (const std::invalid_argument&) { return 1; }
    return std::cout ? 0 : 2;
}
