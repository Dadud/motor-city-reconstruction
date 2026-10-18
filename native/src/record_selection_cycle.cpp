#include "mco/record_selection_cycle.hpp"
#include "mco/record_mode_apply.hpp"
#include "mco/record_selection_apply.hpp"
#include "mco/record_handler.hpp"
#include "mco/record_transition.hpp"
#include "mco/camera_context_special.hpp"
#include "mco/detail/record_selection.hpp"
#include <bit>
#include <stdexcept>
namespace mco {
void record_selection_cycle(RecordMachine& machine,std::span<const std::byte> pairs,
    std::span<const std::byte,36> modes,std::span<const std::byte,12> context,
    std::uint32_t mode,std::uint32_t& counter0,std::uint32_t& counter1,
    std::span<const std::byte> subjects,std::uint32_t viewport) {
    machine.check();
    const auto current=machine.record(machine.load(record_machine_image::current_record));
    const auto old_identifier=detail::read_word(current,state_record::identifier);
    if(old_identifier==10) return;
    const std::uint64_t offset=std::uint64_t(viewport)*4;
    constexpr auto reference_offset=camera_subjects::reference;
    if(offset+reference_offset+4>subjects.size())
        throw std::invalid_argument("camera subject index outside supplied table");
    const auto subject=detail::read_word(subjects,static_cast<std::size_t>(offset));
    const auto reference=detail::read_word(subjects,static_cast<std::size_t>(offset)+reference_offset);
    if(subject!=reference) {
        if(old_identifier==27 || old_identifier==11) return;
        auto index=machine.load(record_machine_image::state_flag);
        std::uint32_t identifier=4;
        for(unsigned attempts=0;attempts<9;++attempts) {
            const auto next=std::bit_cast<std::int32_t>(index+1u) % 9;
            if(next<0) throw std::invalid_argument("negative cycled camera mode index");
            index=static_cast<std::uint32_t>(next);
            identifier=detail::read_word(modes,static_cast<std::size_t>(index)*4);
            if(identifier!=4) break;
        }
        if(identifier==4) throw std::invalid_argument("camera mode table never leaves four");
        // The original stores the index only after finding a non-four entry.
        machine.store(record_machine_image::state_flag,index);
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
        return;
    }
    if(record_handler(old_identifier)!=0x42f8f0u) return;
    detail::normalize_record_selection(machine);
    auto slot=machine.selection_slot;
    for(unsigned attempts=0;attempts<4;++attempts) {
        slot=(slot+1u)&3u;
        if(machine.selection_presets[slot]!=0) break;
    }
    machine.selection_slot=slot;
    const auto preset=std::bit_cast<std::int32_t>(machine.selection_presets[slot]);
    // Negative nonzero presets stop the scan but do not apply a selection.
    if(preset<=0) return;
    machine.selection_index=static_cast<std::uint32_t>(preset)-1u;
    if((mode & 255u)==0)
        record_selection_apply(machine,pairs,modes,context,0,counter0,counter1);
    else
        record_mode_apply(machine,pairs,modes,context,mode,counter0,counter1,
                          machine.load(record_machine_image::state_flag));
}
}
