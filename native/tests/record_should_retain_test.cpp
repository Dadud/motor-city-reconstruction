#include "mco/record_should_retain.hpp"
#include <stdexcept>
int main() {
    std::array<std::byte,256> record{};
    std::array<std::byte,16> request{};
    record[4] = std::byte{14}; request[0] = std::byte{14};
    if (mco::record_should_retain(record, request, 0) != 1)
        throw std::runtime_error("same identifier fourteen must retain the record");
}
