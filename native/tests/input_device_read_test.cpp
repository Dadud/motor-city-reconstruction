#include "input_device_cases.hpp"
#include <stdexcept>
#include <algorithm>
int main(){
    using input_device_cases::Fixture;
    auto require=[](bool ok,const char* message){if(!ok)throw std::runtime_error(message);};
    Fixture f;f.config={2,4,0,15,0x8007000c,0xffffffff,0,0x80004005,0x8007001e,0};
    f.initialize();auto d=f.state();
    require(f.run(d)==0x80004005,"failed second acquisition status not returned");
    const std::array<unsigned,5> methods{0x64,0x1c,0x64,0x24,0x1c};
    require(f.logs.size()==methods.size(),"poll/read retry sequence changed");
    for(unsigned i=0;i<methods.size();++i){
        require(f.logs[i][0]==methods[i] && f.logs[i][1]==(i&1),"virtual table not reloaded");
    }
    for(unsigned i=0;i<4;++i)require(f.buffer[i]==std::byte{},"failed read not cleared");
    require(f.buffer[4]!=std::byte{},"clear exceeded requested size");
    Fixture success;success.config={2,4,0,0,0x80004005,0,0,0,0,0};success.initialize();auto sd=success.state();
    require(success.run(sd)==0 && success.logs.size()==2,"poll failure prevented successful read");
    require(success.buffer[0]==std::byte{74},"successful read data cleared");
    Fixture retry;retry.config={1,1,0,0,0,0,0,0,0x8007000c,0x8007001e};retry.initialize();auto rd=retry.state();
    require(retry.run(rd)==0x8007001e && retry.logs.size()==3,"read retried more than once");
    require(retry.buffer[0]==std::byte{111},"retry helper cleared failed data");
    Fixture zero;zero.config={2,0,0,0,0,0,0,0,1,0};zero.initialize();auto zd=zero.state();const auto before=zero.storage;
    require(zero.run(zd)==1 && std::equal(zero.buffer.begin(),zero.buffer.end(),before.begin()),"zero-size failure changed buffer");
}
