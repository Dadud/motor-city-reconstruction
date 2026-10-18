#pragma once
#include "mco/input_keyboard_layout.hpp"
#include "input_queue_cases.hpp"
namespace input_keyboard_layout_cases {
struct Fixture {
    std::array<std::uint32_t,4> config{};
    std::array<std::byte,scan_translation_tables::size> tables{};
    mco::InputKeyboardLayoutPlatform platform{query,this};
    std::vector<std::array<std::uint32_t,6>> logs;
    static std::uint32_t observe(mco::InputKeyQueue& q,std::uint32_t kind,void* user,bool alternate) {
        auto& f=*static_cast<Fixture*>(user);
        if(kind>1)throw std::invalid_argument("keyboard type kind");
        const auto offset=scan_translation_tables::keyboard_remap;
        f.logs.push_back({alternate?1u:0u,kind,q.load(input_queue_image::remap),q.load(input_queue_image::raw_mode),std::to_integer<std::uint32_t>(f.tables[offset+17]),std::to_integer<std::uint32_t>(f.tables[offset+42])});
        const auto script=f.config[2];
        if(script&1)f.platform.query=second;
        if(script&2)q.store(input_queue_image::remap,q.load(input_queue_image::remap)?0u:0x71002000u);
        if(script&4)f.tables[offset+17]=static_cast<std::byte>((f.config[3]+f.logs.size())&255);
        if(script&8)q.store(input_queue_image::raw_mode,q.load(input_queue_image::raw_mode)^1);
        if((script&16) && kind==1)q.store(input_queue_image::remap,0xdeadbeef);
        return alternate?(kind==0?7u:0xd04u):f.config[kind];
    }
    static std::uint32_t query(mco::InputKeyQueue& q,std::uint32_t kind,void* user){return observe(q,kind,user,false);}
    static std::uint32_t second(mco::InputKeyQueue& q,std::uint32_t kind,void* user){return observe(q,kind,user,true);}
    void emit()const {
        cell_io::emit(platform.query==second?1u:0u);cell_io::emit(tables);cell_io::emit(static_cast<std::uint32_t>(logs.size()));
        for(const auto& row:logs)cell_io::emit(row);
    }

};
inline void compare(std::istream& input){
    Fixture f;for(auto& v:f.config)v=cell_io::read(input);
    auto queue=queue_cases::Fixture::read(input);auto q=queue.state();f.tables=cell_io::image<scan_translation_tables::size>(input);
    cell_io::emit(mco::input_keyboard_layout(q,f.platform));queue.emit();f.emit();
}
}
