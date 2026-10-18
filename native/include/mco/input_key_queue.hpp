#pragma once
#include "mco/detail/byte_words.hpp"
#include "mco/layouts.hpp"
#include <span>
#include <cstdint>
#include <stdexcept>
namespace mco {
inline constexpr std::uint32_t input_queue_address=0xaca8f0;
struct InputKeyQueue;
using InputQueueSync=void (*)(InputKeyQueue&,bool entering,std::uint32_t identity,void* user);
// Observation images, not a recovered original class or Windows lock object.
struct InputKeyQueue {
    const std::span<std::byte,input_queue_image::size> globals;
    const std::span<std::byte,256> keys;
    InputQueueSync sync;
    void* user;
    std::uint32_t load(std::size_t offset) const {return detail::read_word(globals,offset);}
    void store(std::size_t offset,std::uint32_t value) {detail::write_word(globals,offset,value);}
    std::span<std::byte,4> event(std::uint32_t index) const {
        const auto address=input_queue_address+static_cast<std::uint32_t>(input_queue_image::events)+index*4u;
        if(address<input_queue_address || std::uint64_t(address-input_queue_address)+4>globals.size())
            throw std::invalid_argument("queue event outside supplied global image");
        return std::span<std::byte,4>(globals.data()+(address-input_queue_address),4);
    }
    void synchronize(bool entering) {
        if(!sync) throw std::invalid_argument("input queue synchronization implementation required");
        sync(*this,entering,load(input_queue_image::synchronizer),user);
    }
};
}
