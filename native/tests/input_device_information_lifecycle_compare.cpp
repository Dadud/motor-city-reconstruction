#include "input_device_state_cases.hpp"
#include "input_device_information_cases.hpp"
#include "mco/input_device_information_binding.hpp"
int main(){
    return cell_io::run([](std::istream& input){
        input_device_state_cases::Fixture access;
        for(auto& v:access.config)v=cell_io::read(input);
        access.initialize();auto state=access.state();access.access=&state;
        input_device_information_cases::Fixture information;
        for(auto& v:information.config)v=cell_io::read(input);
        information.output=state.information;information.initialize();
        mco::InputDeviceInformationBinding binding{information.platform()};binding.bind(state);
        const auto count=cell_io::read(input);
        if(count==0 || count>4096)throw std::invalid_argument("information lifecycle count");
        for(unsigned i=0;i<count;++i){
            const auto kind=cell_io::read(input);const auto result=mco::input_device_state(state,kind);
            cell_io::emit(result.empty()?0u:result.data()==access.keyboard.data()?0xb36460u:0xb36240u);
            access.emit(state);information.emit(access.device);
        }
    });
}
