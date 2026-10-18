#pragma once
#include "mco/window_dispatch_state.hpp"
#include <bit>
namespace mco::detail {
// Original CRT quicksort specialized to 8-byte records and its fixed comparator.
inline void window_dispatch_sort(WindowDispatchState& state,std::uint32_t count) {
    if(count>128) throw std::invalid_argument("window sort exceeds supplied table");
    auto address=[](int index) {return input_queue_image::message_handlers+static_cast<unsigned>(index)*8;};
    auto compare=[&](int a,int b) {return std::bit_cast<std::int32_t>(state.load(address(a))-state.load(address(b)));};
    auto swap=[&](int a,int b) {
        if(a==b) return;
        const auto key=state.load(address(a)),handler=state.load(address(a)+4);
        state.store(address(a),state.load(address(b)));state.store(address(a)+4,state.load(address(b)+4));
        state.store(address(b),key);state.store(address(b)+4,handler);
    };
    auto sort=[&](auto&& self,int low,int high) -> void {
        const auto length=high-low+1;
        if(length<=8) {
            for(int end=high;low<end;--end) {
                int maximum=low;
                for(int i=low+1;i<=end;++i) if(compare(i,maximum)>0) maximum=i;
                swap(maximum,end);
            }
            return;
        }
        swap(low+length/2,low);
        int left=low,right=high+1;
        for(;;) {
            do {++left;} while(left<=high && compare(left,low)<=0);
            do {--right;} while(right>low && compare(right,low)>=0);
            if(left>right) break;
            swap(left,right);
        }
        swap(low,right);
        // Same smaller-partition-first order as the original explicit stack.
        if(right-low<high-left+1) {
            if(low+1<right) self(self,low,right-1);
            if(left<high) self(self,left,high);
        } else {
            if(left<high) self(self,left,high);
            if(low+1<right) self(self,low,right-1);
        }
    };
    if(count>=2) sort(sort,0,static_cast<int>(count)-1);
}
}
