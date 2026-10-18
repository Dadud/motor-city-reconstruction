#include "input_device_lifetime_cases.hpp"
int main(){return cell_io::run([](std::istream& input){
    input_device_lifetime_cases::Fixture f;for(auto& v:f.config)v=cell_io::read(input);f.initialize();
    std::array<std::uint32_t,7> values;for(auto& v:values)v=cell_io::read(input);
    auto queue=queue_cases::Fixture::read(input);auto q=queue.state();
    mco::InputDeviceLifetimeState s{q,values[0],values[1],values[2],values[3],values[4],values[5],values[6]};
    const auto count=cell_io::read(input);if(count==0 || count>4096)throw std::invalid_argument("lifetime lifecycle count");
    for(unsigned i=0;i<count;++i){
        for(unsigned j=0;j<3;++j)f.config[j]=cell_io::read(input);
        cell_io::emit(f.run(s));f.emit(s,queue);
    }
});}
