#include "mco/lobby_channel_close.hpp"

#include <array>
#include <cstdio>
#include <iostream>
#include <stdexcept>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

namespace {
std::uint64_t read_u64() {
    std::array<unsigned char,8> bytes{};
    if (!std::cin.read(reinterpret_cast<char*>(bytes.data()), bytes.size()))
        throw std::invalid_argument("truncated channel-close comparison input");
    std::uint64_t value = 0;
    for (unsigned i = 0; i < 8; ++i) value |= std::uint64_t(bytes[i]) << (8 * i);
    return value;
}
template<class Bytes> void emit(const Bytes& bytes) {
    std::cout.write(reinterpret_cast<const char*>(bytes.data()), bytes.size());
}
} // namespace

int main() {
#ifdef _WIN32
    if (_setmode(_fileno(stdin), _O_BINARY) == -1 || _setmode(_fileno(stdout), _O_BINARY) == -1) return 2;
#endif
    try {
        const auto selector = read_u64(), channel = read_u64();
        if (std::cin.peek() != std::char_traits<char>::eof()) throw std::invalid_argument("trailing channel-close comparison bytes");
        const auto arguments = mco::native_close_arguments(selector, channel);
        const mco::ChannelCloseRequest request{channel};
        emit(arguments); emit(request.payload()); emit(mco::encode_nps_frame(request.frame()));
        return std::cout ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
