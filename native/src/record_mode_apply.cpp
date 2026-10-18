#include "mco/record_mode_apply.hpp"
#include "mco/camera_context_special.hpp"
#include "mco/record_handler.hpp"
#include "mco/record_transition.hpp"
#include <bit>
#include <stdexcept>
namespace mco {
void record_mode_apply(RecordMachine& machine,std::span<const std::byte> pairs,
    std::span<const std::byte,36> modes,std::span<const std::byte,12> context,
    std::uint32_t mode,std::uint32_t& counter0,std::uint32_t& counter1,
    std::uint32_t index) {
    machine.check();
    const auto signed_index=std::bit_cast<std::int32_t>(index);
    if(signed_index>=9) return;
    if(signed_index<0) throw std::invalid_argument("negative camera mode index");
    auto identifier=detail::read_word(modes,static_cast<std::size_t>(index)*4);
    if(identifier==23) {
        counter0=counter1=10;
        if((mode & 255u)==0) {
            machine.store(record_machine_image::request_flag,2);
            identifier=8;
        } else {
            machine.store(record_machine_image::request_flag,
                          camera_context_special(context) ? 1u : 4u);
            identifier=12;
        }
    } else machine.store(record_machine_image::request_flag,0);
    record_transition(machine,pairs,identifier,record_handler(identifier),0,0);
}
}
