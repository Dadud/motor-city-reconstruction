#include "mco/input_key_query.hpp"
#include <stdexcept>
int main() {
    std::array<std::byte,128> keys{};
    std::array<std::byte,512> latches{};
    keys[1]=std::byte{128};
    if(!mco::input_key_query(keys,latches,1,1) || latches[1]!=std::byte{255}
       || mco::input_key_query(keys,latches,1,1)!=0 || latches[1]!=std::byte{128})
        throw std::runtime_error("press consumption changed");
    keys[1]=std::byte{};
    if(mco::input_key_query(keys,latches,1,1)!=0 || latches[1]!=std::byte{})
        throw std::runtime_error("release must clear latch");
    keys[1]=std::byte{1};
    if(!mco::input_key_query(keys,latches,1,0) || latches[1]!=std::byte{}
       || !mco::input_key_query(keys,latches,1,1))
        throw std::runtime_error("level query must not consume first press");
    latches[257]=std::byte{255};
    if(mco::input_key_query(keys,latches,257,1)!=0 || latches[257]!=std::byte{})
        throw std::runtime_error("out-of-range raw query must still clear mapped latch");
    try {mco::input_key_query(keys,latches,0xffffffffu,1);}
    catch(const std::invalid_argument&) {return 0;}
    throw std::runtime_error("negative latch access accepted");
}
