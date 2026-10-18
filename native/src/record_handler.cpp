#include "mco/record_handler.hpp"
#include <bit>
#include <stdexcept>

namespace mco {
std::uint32_t record_handler(std::uint32_t identifier) {
    switch (identifier) {
    case 0: case 1: case 2: case 3: return 0x42f630;
    case 4: case 5: case 6: case 7: case 8: case 9: case 10: case 11:
    case 18: case 19: case 20: case 21: case 22: return 0x42f8f0;
    case 14: return 0x432bc0;
    case 15: case 16: return 0x431ba0;
    case 17: case 26: case 27: case 28: return 0x432730;
    case 24: case 25: return 0x432180;
    case 29: return 0x433820;
    default: return 0x433200;
    }
}
}
