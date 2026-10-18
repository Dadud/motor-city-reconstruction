#include "mco/input_queue_resize.hpp"
#include "input_queue_cases.hpp"
#include <stdexcept>
int main() {
    for(auto request : {0u,1u,32u,33u,0x80000000u,0xffffffffu}) {
        queue_cases::Fixture f;
        auto s=f.state();
        s.store(input_queue_image::read_cursor,7);
        s.store(input_queue_image::write_cursor,9);
        s.store(input_queue_image::target_window,0x1234);
        mco::input_queue_resize(s,request);
        const auto expected=(request==32u || request==33u) ? 32u : 1u;
        if(s.load(input_queue_image::capacity)!=expected ||
           s.load(input_queue_image::read_cursor)!=0 ||
           s.load(input_queue_image::write_cursor)!=0 ||
           s.load(input_queue_image::target_window)!=0x1234 || !f.logs.empty())
            throw std::runtime_error("resize clamp or state isolation changed");
    }
}
