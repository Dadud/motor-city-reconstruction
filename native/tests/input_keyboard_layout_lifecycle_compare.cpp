#include "input_keyboard_layout_cases.hpp"
#include "input_translation_cases.hpp"
#include "mco/window_keyboard_layout_binding.hpp"
#include "mco/input_key_release.hpp"
#include "mco/input_key_query.hpp"
#include "mco/input_queue_peek.hpp"
#include "mco/input_queue_pop.hpp"
int main(){return cell_io::run([](std::istream& input){
    input_keyboard_layout_cases::Fixture layout;for(auto& v:layout.config)v=cell_io::read(input);
    input_translation_cases::Fixture t;for(auto& v:t.config)v=cell_io::read(input);t.initialize();auto translation=t.state();
    auto queue=queue_cases::Fixture::read(input);auto q=queue.state();layout.tables=cell_io::image<scan_translation_tables::size>(input);
    translation.tables=layout.tables;auto latches=cell_io::image<512>(input);
    const auto count=cell_io::read(input);if(count==0 || count>4096)throw std::invalid_argument("layout session count");
    for(unsigned i=0;i<count;++i){
        const auto op=cell_io::read(input),a=cell_io::read(input),b=cell_io::read(input),c=cell_io::read(input),d=cell_io::read(input),e=cell_io::read(input);
        std::uint32_t result=0;
        if(op==0)result=mco::input_keyboard_layout(q,layout.platform);
        else if(op==1)result=mco::window_keyboard_layout_binding(q,layout.tables,queue.remap,0x584450,a,b,c,d,e);
        else if(op==2)result=mco::input_queue_peek(q,translation);
        else if(op==3)result=mco::input_queue_pop(q,translation);
        else if(op==4)result=mco::window_keyboard_layout_binding(q,layout.tables,queue.remap,0x584610,a,b,c,d,e);
        else if(op==5)result=mco::input_key_query(std::span<const std::byte,128>(queue.keys.data(),128),latches,a,b);
        else if(op==6){if(a>=128 || b>255)throw std::invalid_argument("layout fixture byte");layout.tables[scan_translation_tables::keyboard_remap+a]=static_cast<std::byte>(b);}
        else if(op==7)result=mco::input_scan_translate(translation,a,b);
        else if(op==8)q.store(input_queue_image::remap,a);
        else throw std::invalid_argument("layout session operation");
        cell_io::emit(result);queue.emit();layout.emit();cell_io::emit(translation.caps);cell_io::emit(translation.escape_exits);
        cell_io::emit(static_cast<std::uint32_t>(t.logs.size()));for(const auto& row:t.logs)cell_io::emit(row);
        cell_io::emit(t.device);cell_io::emit(latches);
    }
});}
