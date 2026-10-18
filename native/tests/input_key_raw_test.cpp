#include "mco/input_key_raw.hpp"
#include <stdexcept>
int main() {
    std::array<std::byte,128> keys{};keys[0]=std::byte{128};keys[127]=std::byte{3};
    if(mco::input_key_raw(keys,0)!=128 || mco::input_key_raw(keys,128)!=128
       || mco::input_key_raw(keys,256)!=0 || mco::input_key_raw(keys,0x7fffffffu)!=0
       || mco::input_key_raw(keys,0x80000000u)!=128 || mco::input_key_raw(keys,0xffffffffu)!=3)
        throw std::runtime_error("signed key range or raw-byte alias changed");
}
