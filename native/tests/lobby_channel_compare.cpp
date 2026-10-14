#include "mco/lobby_channel_codec.hpp"
#include <array>
#include <iostream>
#include <stdexcept>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif
int main() {
#ifdef _WIN32
    _setmode(_fileno(stdin), _O_BINARY);
    _setmode(_fileno(stdout), _O_BINARY);
#endif
    try {
        std::array<std::uint8_t, mco::channel_record_size> record;
        if (!std::cin.read(reinterpret_cast<char*>(record.data()), record.size()) ||
            std::cin.peek() != std::char_traits<char>::eof()) return 2;
        const auto output = mco::encode_channel_join_payload(record);
        std::cout.write(reinterpret_cast<const char*>(output.data()), output.size());
        return 0;
    } catch (const std::invalid_argument&) { return 1; }
}
