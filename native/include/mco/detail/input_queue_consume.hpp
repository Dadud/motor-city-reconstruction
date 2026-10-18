#pragma once
#include "mco/input_key_queue.hpp"
#include "mco/input_scan_translate.hpp"
#include <bit>
namespace mco::detail {
inline std::uint32_t input_queue_consume(InputKeyQueue& queue,InputTranslationState& translation,bool remove) {
    std::uint32_t value=0,scan=0;
    queue.synchronize(true);
    auto head=queue.load(input_queue_image::read_cursor);
    auto advance=[&]() {
        const auto capacity=std::bit_cast<std::int32_t>(queue.load(input_queue_image::capacity));
        if(capacity<=0)throw std::invalid_argument("queue consumer capacity must be positive at division");
        head=std::bit_cast<std::uint32_t>(std::bit_cast<std::int32_t>(head+1u)%capacity);
        queue.store(input_queue_image::read_cursor,head);
    };
    while(head!=queue.load(input_queue_image::write_cursor)) {
        if(value!=0)break;
        const auto word=read_word(queue.event(head),0);
        value=static_cast<std::uint32_t>(static_cast<std::int32_t>(std::bit_cast<std::int16_t>(static_cast<std::uint16_t>(word>>16))));
        scan=(word>>8)&255u;
        if(value==0) {
            value=input_scan_translate(translation,scan,word&255u);
            head=queue.load(input_queue_image::read_cursor);
            if(remove || value==0)advance();
        } else if(remove)advance();
    }
    queue.synchronize(false);
    return (scan<<16)|value;
}
}
