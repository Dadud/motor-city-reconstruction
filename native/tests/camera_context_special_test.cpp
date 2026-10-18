#include "mco/camera_context_special.hpp"
#include "mco/detail/byte_words.hpp"
#include <stdexcept>
int main() {
    std::array<std::byte,12> context{};
    if(mco::camera_context_special(context)) throw std::runtime_error("default context");
    mco::detail::write_word(context,8,24);
    if(!mco::camera_context_special(context)) throw std::runtime_error("secondary context");
    mco::detail::write_word(context,8,25);
    if(mco::camera_context_special(context)) throw std::runtime_error("secondary boundary");
    mco::detail::write_word(context,0,18);
    if(!mco::camera_context_special(context)) throw std::runtime_error("primary context");
}
