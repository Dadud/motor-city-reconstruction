#include "input_device_lifetime_cases.hpp"
#include <stdexcept>
#include "input_device_state_cases.hpp"
#include "mco/input_device_lifetime_access.hpp"
#include "input_translation_cases.hpp"
int main(){
    using namespace mco;
    auto require=[](bool ok,const char* message){if(!ok)throw std::runtime_error(message);};
    queue_cases::Fixture qf;auto q=qf.state();q.store(input_queue_image::dispatch_synchronizer,0);
    input_device_lifetime_cases::Fixture f;f.config={4,0,0,0x71001400,4,8,0};f.initialize();
    std::array<std::uint32_t,4> globals{};
    InputDeviceLifetimeState state{q,globals[0],globals[1],0,0,0,globals[2],globals[3]};
    require(f.run(state)==9 && state.interface_handle==0 && state.device==0,"failed setup lost initialization flag or cleanup");
    require(q.load(input_queue_image::raw_mode)==7 && q.load(input_queue_image::capacity)==32 && q.load(input_queue_image::read_cursor)==0 && q.load(input_queue_image::write_cursor)==0,"factory mutations or subsequent resize order changed");
    require(state.cleanup_registered==1,"failed setup skipped cleanup registration");
    f.config[4]=0;f.config[5]=128|64;f.logs.clear();
    require(f.run(state)==9 && state.device==0x71001300,"successful setup did not reload changed device");
    bool released_replacement=false,cooperative=false;
    for(const auto& row:f.logs){
        if(row[0]==8 && row[1]==0x71001500)released_replacement=true;
        if(row[0]==0x34 && row[1]==0x71001300 && row[5]==0xdeadbeef && row[6]==6)cooperative=true;
    }
    require(released_replacement && cooperative,"temporary reload or cooperative arguments changed");
    f.logs.clear();f.run(state);require(f.logs.empty(),"repeated initialization repeated setup");
    f.config[0]=0;f.config[5]=1;f.logs.clear();f.run(state);
    require(f.logs[1][0]==8 && f.logs[1][1]==0x71001300 && state.device==0 && state.interface_handle==0,"cleanup did not reload handles");
    f.config[0]=1;f.run(state);require(state.initialized==0 && state.cleanup_registered==1,"shutdown reset wrong flags");
    f.config={4,0,0,0x71001400,0,16,0};f.temporary=nullptr;state.cleanup_registered=0;
    require(f.run(state)==0x1234 && state.cleanup_registered==1,"registration callback writes or returned flag changed");
    f.config[0]=2;f.config[1]=6;f.config[5]=256;require(f.run(state)==0 && state.initialized==555 && state.diagnostic_line==0x117,"invalid set-state diagnostic order/return changed");
    f.config[1]=10;f.config[2]=0xffffffff;require(f.run(state)==1 && state.callback==0xffffffff,"callback setter changed");
    // Alias the real globals rather than copying handles between controllers.
    input_device_state_cases::Fixture acquisition;acquisition.config={6,1,73,0,0,0,0,0,0,0,0,0};acquisition.initialize();
    auto views=acquisition.state();auto access=input_device_access_from_lifetime(state,views);acquisition.access=&access;
    f.config={1,0,0,0x71001400,0,0,0};f.run(state);
    f.config[0]=4;f.run(state);acquisition.device.identity=state.device;
    require(access.enabled==state.interface_handle && access.device==state.device,"lifetime handles were copied into acquisition");
    require(input_device_state(access,6).size()==260,"shared initialized handles did not acquire state");
    const auto acquired=acquisition.methods.logs.size();
    f.config[0]=0;f.run(state);
    require(access.enabled==0 && access.device==0 && input_device_state(access,6).empty() && acquisition.methods.logs.size()==acquired,"cleanup did not disable shared acquisition");
    f.config[0]=2;f.config[1]=6;f.run(state);
    require(access.diagnostic_file==0x84a0f0 && access.diagnostic_line==0x117,"diagnostic globals were copied between views");
    input_translation_cases::Fixture alias;alias.config={112,0,1,1,0,0,0,0,256,1,1};alias.initialize();
    input_device_bind_callback_table(state,alias.tables);auto translated=alias.state();
    input_device_set_state(state,f.platform(),10,0x81807f41);
    const std::array<unsigned,4> first{65,127,0x8000,0x8100};
    for(unsigned i=0;i<4;++i)require(input_scan_translate(translated,112+i,0)==first[i],"callback setter did not update overlapping scan bytes");
    alias.tables[scan_translation_tables::callback_word]=std::byte{255};
    require(static_cast<std::uint32_t>(state.callback)==0x81807fff,"callback read ignored changed table bytes");
    input_device_set_state(state,f.platform(),10,0x00ff908f);
    const std::array<unsigned,4> second{0x8f00,0x1000,0x7f00,0};
    for(unsigned i=0;i<4;++i)require(input_scan_translate(translated,112+i,1)==second[i],"callback alias encoding changed");

}
