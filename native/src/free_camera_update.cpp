#include "mco/free_camera_update.hpp"
#include <stdexcept>
#include "mco/input_key_query.hpp"
#include "mco/camera_matrix_rotation.hpp"
#include "mco/track_surface_lookup.hpp"

namespace mco {

// Decompiled pseudocode of 0x433820, kept as the implementation draft.
// The oracle against the original, not this text, decides correctness.


void free_camera_update(FreeCameraState &state, const TrackSurfaceWorld &world, std::uint32_t event, std::uint32_t reset_time) {
    using namespace free_camera_image;
    auto load=[&](std::size_t o) {return detail::read_word(state.image,o);};
    auto store=[&](std::size_t o,std::uint32_t v) {detail::write_word(state.image,o,v);};
    auto real=[&](std::size_t o) {return std::bit_cast<float>(load(o));};
    auto save=[&](std::size_t o,float v) {store(o,std::bit_cast<std::uint32_t>(v));};
    auto copy=[&](std::size_t to,std::size_t from,unsigned words) {
        for(unsigned i=0;i<words;++i) store(to+i*4,load(from+i*4));
    };
    auto reset=[&] {
        store(free_camera_image::reset_time,reset_time);
        copy(position,saved_position,3);copy(matrix,saved_matrix,9);
        store(sensitivity,load(saved_sensitivity));store(auxiliary,load(saved_auxiliary));
        copy(surface,saved_surface,17);store(subject,load(saved_subject));store(active,1);
    };
    if(event==0) {reset();return;}
    if(event!=1) return;
    auto key=[&](std::uint32_t code,std::uint32_t press=0) {
        return input_key_query(state.keys,state.latches,code,press)!=0;
    };
    float rate=key(0x38) ? 4.f : 1.f;
    if(key(0x1d) || key(0x9d)) rate=static_cast<float>(static_cast<double>(rate)*0.10000000149011612);
    if(key(0x13,1)) reset();
    if(key(0xd2)) save(sensitivity,static_cast<float>(static_cast<double>(real(sensitivity))*1.0499999523162842));
    if(key(0xd3) && real(sensitivity)>0.30000001192092896f)
        save(sensitivity,static_cast<float>(static_cast<double>(real(sensitivity))*0.949999988079071));
    rate=static_cast<float>(static_cast<double>(rate)/real(sensitivity));
    // Original 0x413810 is RET, with no state changes or argument reads.
    auto shift=[&] {return key(0x2a) || key(0x36);};
    std::array<float,9> orientation;
    for(unsigned i=0;i<9;++i) orientation[i]=real(matrix+i*4);
    auto rotate=[&](std::uint32_t code,unsigned axis,double factor) {
        if(shift() && key(code)) {
            camera_matrix_rotation(orientation,static_cast<float>(static_cast<double>(rate)*factor),orientation,axis);
            for(unsigned i=0;i<9;++i) save(matrix+i*4,orientation[i]);
        }
    };
    rotate(0xcd,1,0.009999999776482582);rotate(0xcb,1,-0.009999999776482582);
    rotate(0xd0,0,-0.009999999776482582);rotate(0xc8,0,0.009999999776482582);
    rotate(0xc9,2,-0.009999999776482582);rotate(0xd1,2,0.009999999776482582);
    save(motion,0);save(motion+4,0);save(motion+8,0);
    if(!shift() && key(0xc8)) save(motion+4,static_cast<float>(static_cast<double>(rate)*0.5));
    if(!shift() && key(0xd0)) save(motion+4,static_cast<float>(real(motion+4)-static_cast<double>(rate)*0.5));
    if(!shift() && key(0xcb)) save(motion,static_cast<float>(static_cast<double>(rate)*-0.5));
    if(!shift() && key(0xcd)) save(motion,static_cast<float>(static_cast<double>(rate)*0.5+real(motion)));
    if(!shift() && key(0xc9)) save(motion+8,static_cast<float>(static_cast<double>(rate)*0.5));
    if(!shift() && key(0xd1)) save(motion+8,static_cast<float>(real(motion+8)-static_cast<double>(rate)*0.5));
    if(real(motion)!=0 || real(motion+4)!=0 || real(motion+8)!=0) {
        std::array<float,3> displacement;
        for(unsigned j=0;j<3;++j)
            displacement[j]=static_cast<float>(static_cast<double>(real(motion+8))*orientation[6+j]+
                static_cast<double>(real(motion+4))*orientation[3+j]+static_cast<double>(real(motion))*orientation[j]);
        for(unsigned j=0;j<3;++j) save(position+j*4,static_cast<float>(static_cast<double>(real(position+j*4))+displacement[j]));
    }
    if(load(subject)!=0) {
        if(!state.resolve_subject) throw std::invalid_argument("camera subject resolver required");
        const auto subject_surface=state.resolve_subject(load(subject),state.user);
        for(unsigned j=0;j<17;++j) store(surface+j*4,detail::read_word(subject_surface,j*4));
    }
    std::array<float,3> location;
    for(unsigned j=0;j<3;++j) location[j]=real(position+j*4);
    track_surface_lookup(world,location,std::span<std::byte,68>(state.image.data()+surface,68));
}

}  // namespace mco
