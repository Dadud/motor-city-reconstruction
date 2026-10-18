#include "input_queue_cases.hpp"
#include "input_translation_cases.hpp"
#include "input_device_state_cases.hpp"
#include "mco/input_translation_device_binding.hpp"
#include "mco/input_character.hpp"
#include "mco/input_queue_pop.hpp"
#include "mco/input_queue_peek.hpp"
#include "mco/input_key_down.hpp"
#include "mco/input_key_query.hpp"
#include "mco/input_key_release.hpp"
#include "mco/input_queue_resize.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        input_translation_cases::Fixture t;
        for(auto& v:t.config)v=cell_io::read(input);
        t.initialize();auto translation=t.state();
        input_device_state_cases::Fixture acquisition;
        for(auto& v:acquisition.config)v=cell_io::read(input);
        acquisition.initialize();auto access=acquisition.state();acquisition.access=&access;
        mco::InputTranslationDeviceBinding binding{access,input_translation_cases::Fixture::exit_request,&t};
        binding.bind(translation);
        auto f=queue_cases::Fixture::read(input);
        auto latches=cell_io::image<512>(input);
        auto state=f.state();
        const auto count=cell_io::read(input);
        if(count==0 || count>4096) throw std::invalid_argument("queue lifecycle count");
        for(std::uint32_t i=0;i<count;++i) {
            const auto op=cell_io::read(input);
            const auto a=cell_io::read(input),b=cell_io::read(input),c=cell_io::read(input);
            const auto d=cell_io::read(input),e=cell_io::read(input);
            std::uint32_t result=0;
            if(op==0) result=mco::input_key_down(state,f.remap,a,b,c,d,e);
            else if(op==1) result=mco::input_key_query(std::span<std::byte,128>(f.keys.data(),128),latches,a,b);
            else if(op==2) result=mco::input_key_release(f.keys,f.remap,state.load(input_queue_image::remap),a,b,
                                                      state.load(input_queue_image::target_window),e);
            else if(op==3) mco::input_queue_resize(state,a);
            else if(op==4) result=mco::input_character(state,a,b,c,d,e);
            else if(op==5) result=mco::input_queue_peek(state,translation);
            else if(op==6) result=mco::input_queue_pop(state,translation);
            else throw std::invalid_argument("queue lifecycle operation");
            cell_io::emit(result);f.emit();cell_io::emit(latches);
            cell_io::emit(translation.caps);cell_io::emit(translation.escape_exits);
            cell_io::emit(static_cast<std::uint32_t>(t.logs.size()));
            for(const auto& row:t.logs)cell_io::emit(row);
            cell_io::emit(t.device);cell_io::emit(t.tables);acquisition.emit(access);
        }
    });
}
