#pragma once
#include "mco/detail/byte_words.hpp"
namespace mco {
// Opaque callback identity, never a host function pointer. A bound word shares
// bytes with the supplied lookup window; unbound instances retain a value.
class InputDeviceCallback {
    std::uint32_t value_{};
    std::span<std::byte> bytes_{};
public:
    InputDeviceCallback(std::uint32_t value=0):value_(value){}
    operator std::uint32_t() const {return bytes_.empty()?value_:detail::read_word(bytes_,0);}
    InputDeviceCallback& operator=(std::uint32_t value){
        if(bytes_.empty())value_=value;else detail::write_word(bytes_,0,value);
        return *this;
    }
    void bind(std::span<std::byte,4> bytes){
        const auto current=static_cast<std::uint32_t>(*this);
        bytes_=bytes;detail::write_word(bytes_,0,current);
    }
};
}
