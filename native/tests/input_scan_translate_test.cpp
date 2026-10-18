#include "input_translation_cases.hpp"
#include <stdexcept>
int main() {
    input_translation_cases::Fixture f;
    f.config={17,0xffffffff,0,255,0,0,0,0,256,1,1};f.initialize();f.device.fill(std::byte{});
    const std::array<unsigned,5> values{65,66,67,0x81,0x91};
    for(unsigned i=0;i<5;++i)f.tables[i*91+17]=static_cast<std::byte>(values[i]);
    auto state=f.state();
    if(mco::input_scan_translate(state,17,0)!=65)throw std::runtime_error("normal plane changed");
    state.caps=1;
    if(mco::input_scan_translate(state,17,0)!=67)throw std::runtime_error("caps plane changed");
    f.device[direct_key_image::shift_left]=std::byte{1};
    if(mco::input_scan_translate(state,17,0)!=66)throw std::runtime_error("shift priority changed");
    f.device[direct_key_image::control_right]=std::byte{128};
    if(mco::input_scan_translate(state,17,0)!=0x8100)throw std::runtime_error("control encoding changed");
    f.device[direct_key_image::alt_right]=std::byte{255};
    if(mco::input_scan_translate(state,17,0)!=0x1100)throw std::runtime_error("alt priority/encoding changed");
    f.config[9]=0;const auto calls=f.logs.size();
    if(mco::input_scan_translate(state,0x3a,0)!=0 || state.caps!=0 || f.logs.size()!=calls+1)
        throw std::runtime_error("caps toggle skipped provider or dereferenced unused null state");
    f.config[9]=1;f.device.fill(std::byte{});f.device[direct_key_image::control_left]=std::byte{1};
    state.escape_exits=1;
    bool exited=false;
    try {mco::input_scan_translate(state,1,0);}
    catch(const input_translation_cases::ExitRequested&) {exited=true;}
    if(!exited || f.logs.back()[0]!=1 || f.logs.back()[1]!=0)
        throw std::runtime_error("control escape lost exit request");
    f.device[direct_key_image::alt_left]=std::byte{1};
    mco::input_scan_translate(state,1,0); // Alt wins over the control-exit branch.
}
