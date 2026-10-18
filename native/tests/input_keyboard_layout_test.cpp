#include "mco/input_keyboard_layout.hpp"
#include <array>
#include <stdexcept>
using namespace mco;
void require(bool v){if(!v)throw std::runtime_error("keyboard layout invariant");}
struct Calls {
    InputKeyboardLayoutPlatform platform{query,this};unsigned calls{};std::uint32_t type=7,subtype=0xd01;
    static std::uint32_t alternate(InputKeyQueue&,std::uint32_t,void*){throw std::runtime_error("cached query lost");}
    static std::uint32_t query(InputKeyQueue& q,std::uint32_t kind,void* user){
        auto& f=*static_cast<Calls*>(user);require(kind==f.calls++);
        f.platform.query=alternate;q.store(input_queue_image::remap,0x1234);
        return kind==0?f.type:f.subtype;
    }
};
int main(){
    std::array<std::byte,input_queue_image::size> globals{};std::array<std::byte,256> keys{};
    InputKeyQueue q{globals,keys,nullptr,nullptr};Calls f;
    require(input_keyboard_layout(q,f.platform)==1 && f.calls==2);
    require(q.load(input_queue_image::remap)==keyboard_scan_remap_identity);
    for(auto subtype:{0u,0xd00u,0xd05u,0x80000000u,0xffffffffu}){
        Calls g;g.subtype=subtype;require(input_keyboard_layout(q,g.platform)==0 && g.calls==2);
        require(q.load(input_queue_image::remap)==0x1234);
    }
    Calls h;h.type=6;require(input_keyboard_layout(q,h.platform)==0 && h.calls==1);
    std::array<std::byte,scan_translation_tables::size> tables{};auto remap=input_keyboard_remap(tables);
    tables[scan_translation_tables::keyboard_remap+17]=std::byte{42};require(remap[17]==std::byte{42});
}
