#include "mco/pointer_clear_record_c.hpp"
#include <stdexcept>
int main() {
    std::uint32_t record = 0x12345678;
    mco::pointer_clear_record_c({}, 0, record);
    if (record != 0x12345678) throw std::runtime_error("null branch changed record");
}
