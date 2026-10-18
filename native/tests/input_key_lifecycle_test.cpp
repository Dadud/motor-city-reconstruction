#include "input_key_cases.hpp"
#include <stdexcept>
int main() {
    std::array<std::byte,128> keys{};std::array<std::byte,512> latches{};
    const std::array<std::uint32_t,5> raw{128,128,1,0,1};
    const std::array<std::uint32_t,5> expected{1,0,1,0,1};
    for(unsigned k=0;k<raw.size();++k) {
        keys[1]=static_cast<std::byte>(raw[k]);
        if(mco::input_key_query(keys,latches,1,1)!=expected[k])
            throw std::runtime_error("raw-mask transition lifecycle changed");
    }
    if(!mco::input_key_query(keys,latches,129,1) || latches[129]!=std::byte{255})
        throw std::runtime_error("aliased key codes must retain independent latches");
}
