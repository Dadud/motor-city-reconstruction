#include "mco/input_key_release.hpp"
#include "mco/input_key_query.hpp"
#include <stdexcept>
int main() {
    std::array<std::byte,128> keys{};std::array<std::byte,128> remap{};
    std::array<std::byte,512> latches{};
    keys[42]=keys[54]=std::byte{1};
    if(!mco::input_key_query(keys,latches,42,1) || !mco::input_key_query(keys,latches,54,1))
        throw std::runtime_error("shift setup");
    remap[1]=std::byte{42};
    mco::input_key_release(keys,remap,1,1,7,8,1u<<16);
    if(keys[42]==std::byte{}) throw std::runtime_error("foreign window changed key");
    mco::input_key_release(keys,remap,1,1,8,8,1u<<16);
    if(keys[42]!=std::byte{} || keys[54]!=std::byte{}
       || mco::input_key_query(keys,latches,42,1)!=0
       || mco::input_key_query(keys,latches,54,1)!=0)
        throw std::runtime_error("mapped shift release must clear both keys and allow latch release");
    mco::input_key_release({},remap,0,0,0,0,0);
    remap[0]=std::byte{255};
    try {mco::input_key_release(keys,remap,1,1,0,0,0);}
    catch(const std::invalid_argument&) {return 0;}
    throw std::runtime_error("mapped release outside supplied image accepted");
}
