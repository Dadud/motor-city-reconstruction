#include "mco/mod_script.hpp"

#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

namespace {
std::uint32_t number() {
    unsigned char bytes[4];
    if (!std::cin.read(reinterpret_cast<char*>(bytes), 4)) throw std::runtime_error("truncated package");
    return std::uint32_t(bytes[0]) | (std::uint32_t(bytes[1]) << 8) |
           (std::uint32_t(bytes[2]) << 16) | (std::uint32_t(bytes[3]) << 24);
}
std::string field(std::size_t maximum) {
    const auto size = number();
    if (size > maximum) throw std::runtime_error("package field exceeds limit");
    std::string value(size, '\0');
    if (!std::cin.read(value.data(), size)) throw std::runtime_error("truncated package field");
    return value;
}
void quote(std::string_view value) {
    std::cout << '"';
    constexpr char hex[] = "0123456789abcdef";
    for (unsigned char c : value) {
        if (c == '"' || c == '\\') std::cout << '\\' << char(c);
        else if (c < 32 || c >= 127)
            std::cout << "\\u00" << hex[c >> 4] << hex[c & 15];
        else std::cout << char(c);
    }
    std::cout << '"';
}
int report(const mco::ModScriptResult& result) {
    std::cout << "{\"success\":" << (result.success ? "true" : "false") << ",\"error\":";
    quote(result.error);
    std::cout << ",\"resources\":[";
    bool first = true;
    for (const auto& item : result.resources) {
        if (!first) std::cout << ',';
        first = false;
        std::cout << "{\"id\":"; quote(item.id);
        std::cout << ",\"kind\":"; quote(item.kind);
        std::cout << ",\"label\":"; quote(item.label);
        std::cout << '}';
    }
    std::cout << "],\"notes\":[";
    first = true;
    for (const auto& note : result.notes) {
        if (!first) std::cout << ',';
        first = false;
        quote(note);
    }
    std::cout << "]}\n";
    return result.success ? 0 : 1;
}
}

int main(int argc, char** argv) {
#ifdef _WIN32
    _setmode(_fileno(stdin), _O_BINARY);
#endif
    try {
        if (argc != 2 || (std::string_view(argv[1]) != "inspect" && std::string_view(argv[1]) != "preview"))
            throw std::runtime_error("expected inspect or preview event");
        char magic[5];
        if (!std::cin.read(magic, 5) || std::string_view(magic, 5) != "MCOS1")
            throw std::runtime_error("invalid package bridge header");
        mco::ModScriptPackage package;
        package.api_version = "script-alpha-1";
        package.id = field(80);
        package.version = field(64);
        const auto count = number();
        if (count > 256) throw std::runtime_error("resource count exceeds limit");
        for (std::uint32_t i = 0; i < count; ++i) {
            auto id = field(161);
            auto kind = field(16);
            auto label = field(1024);
            package.resources.push_back({std::move(id), std::move(kind), std::move(label)});
        }
        package.source = field(1024 * 1024);
        if (std::cin.peek() != std::char_traits<char>::eof()) throw std::runtime_error("trailing package data");
        const auto event = std::string_view(argv[1]) == "inspect" ?
            mco::ModResearchEvent::inspect : mco::ModResearchEvent::preview;
        return report(mco::run_mod_script(package, event, mco::ModExecutionMode::offline));
    } catch (const std::exception& error) {
        return report({false, error.what(), {}, {}});
    }
}
