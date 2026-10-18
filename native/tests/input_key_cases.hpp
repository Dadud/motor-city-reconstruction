#pragma once
#include "cell_io.hpp"
#include "mco/input_key_query.hpp"
#include "mco/input_key_release.hpp"

namespace input_key_cases {
inline void lifecycle(std::istream& input) {
    auto keys=cell_io::image<128>(input);
    auto latches=cell_io::image<512>(input);
    std::array<std::byte,128> unused_remap{};
    const auto count=cell_io::read(input);
    if(count==0 || count>4096) throw std::invalid_argument("key lifecycle count");
    for(std::uint32_t k=0;k<count;++k) {
        const auto code=cell_io::read(input);
        const auto raw=cell_io::read(input);
        const auto mode=cell_io::read(input);
        if(raw>255) throw std::invalid_argument("raw key byte");
        if(raw==0)
            mco::input_key_release(keys,unused_remap,0,1,7,7,(code&127)<<16);
        else keys[code&127]=static_cast<std::byte>(raw);
        cell_io::emit(mco::input_key_query(keys,latches,code,mode));
        cell_io::emit(keys);cell_io::emit(latches);
    }
}
}
