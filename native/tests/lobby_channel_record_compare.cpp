#include "mco/lobby_channel_record.hpp"

#include <iostream>
#include <string_view>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

// Private binary comparison protocol; no sockets or original host pointers.
// initialize: 0x15c-byte argument followed by explicit 0x3bc-byte allocation.
// materialize: exactly 0x3bc-byte image, including supplied connection overrides.
// Success emits the complete image/record; invalid runner input exits 2.
int main(int argc, char** argv) {
#ifdef _WIN32
    _setmode(_fileno(stdin), _O_BINARY);
    _setmode(_fileno(stdout), _O_BINARY);
#endif
    if (argc != 2) return 2;
    const std::string_view mode(argv[1]);
    const auto expected = mode == "initialize" ? mco::channel_argument_size + mco::channel_allocation_size
        : (mode == "materialize" ? mco::channel_allocation_size : 0);
    if (!expected) return 2;
    std::vector<std::uint8_t> input(expected);
    std::cin.read(reinterpret_cast<char*>(input.data()),static_cast<std::streamsize>(input.size()));
    if (std::cin.gcount() != static_cast<std::streamsize>(input.size())
        || std::cin.peek() != std::char_traits<char>::eof()) return 2;
    if (mode == "initialize") {
        const auto image = mco::initialize_channel_image(std::span(input).first(mco::channel_argument_size),
                                                       std::span(input).subspan(mco::channel_argument_size));
        std::cout.write(reinterpret_cast<const char*>(image.data()),image.size());
    } else {
        const auto record = mco::materialize_channel_record(input);
        std::cout.write(reinterpret_cast<const char*>(record.data()),record.size());
    }
    return std::cout ? 0 : 2;
}
