#pragma once
#include "record_machine_cases.hpp"
#include "mco/record_selection_apply.hpp"
namespace selection_cases {
struct Fixture : record_cases::Fixture {
    std::uint32_t mode{},counter0{},counter1{};
    std::array<std::uint32_t,3> presets{};
    std::array<std::byte,36> modes{};
    std::array<std::byte,12> context{};
    std::array<std::byte,64> pairs{};
    std::vector<std::array<std::uint32_t,5>> extra_logs;
    static Fixture read(std::istream& input) {
        Fixture f;
        f.mode=cell_io::read(input);
        f.modes=cell_io::image<36>(input);
        f.context=cell_io::image<12>(input);
        f.pairs=cell_io::image<64>(input);
        for(auto& value:f.presets) value=cell_io::read(input);
        f.counter0=cell_io::read(input); f.counter1=cell_io::read(input);
        static_cast<record_cases::Fixture&>(f)=record_cases::Fixture::read(input);
        return f;
    }
    static void callback(mco::RecordMachine& machine,std::uint32_t handler,
                         std::uint32_t event,void* user) {
        auto& f=*static_cast<Fixture*>(user);
        f.extra_logs.push_back({machine.selection_presets[1],machine.selection_presets[2],
            machine.selection_presets[3],f.counter0,f.counter1});
        record_cases::Fixture::callback(machine,handler,event,
                                       static_cast<record_cases::Fixture*>(&f));
        if(f.mask & 16) {
            for(unsigned k=0;k<3;++k) machine.selection_presets[k+1]=f.value+k;
            f.counter0=f.value+3u; f.counter1=f.value+4u;
        }
    }
    mco::RecordMachine machine() {
        return {bytes,{count,presets[0],presets[1],presets[2]},index,pending,&callback,this};
    }
    void emit(const mco::RecordMachine& machine) const {
        for(unsigned k=1;k<4;++k) cell_io::emit(machine.selection_presets[k]);
        cell_io::emit(counter0); cell_io::emit(counter1);
        record_cases::Fixture::emit(machine);
        for(const auto& log:extra_logs) cell_io::emit(log);
        cell_io::emit(modes); cell_io::emit(context); cell_io::emit(pairs);
    }
};
inline void lifecycle(Fixture& fixture, mco::RecordMachine& machine) {
    mco::record_machine_initialize(machine);
    mco::record_selection_apply(machine,fixture.pairs,fixture.modes,fixture.context,
                                0,fixture.counter0,fixture.counter1);
    machine.store(record_machine_image::state_flag,2);
    mco::record_selection_apply(machine,fixture.pairs,fixture.modes,fixture.context,
                                1,fixture.counter0,fixture.counter1);
    machine.store(record_machine_image::state_flag,9);
    mco::record_selection_apply(machine,fixture.pairs,fixture.modes,fixture.context,
                                1,fixture.counter0,fixture.counter1);
}
}
