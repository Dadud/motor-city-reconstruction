#include "mco/input_mouse_lifetime.hpp"
#include <initializer_list>
#include <stdexcept>
namespace mco {
namespace {
std::uint32_t call(InputMouseLifetimeState& state,const InputMouseLifetimePlatform& p,
    std::uint32_t code,std::uint32_t identity=0,std::initializer_list<std::uint32_t> args={},
    std::uint32_t slot=0,std::span<std::uint32_t> out={}){
    if(!p.invoke)throw std::invalid_argument("mouse lifetime bridge required");
    return p.invoke(state,code,identity,{args.begin(),args.size()},slot,out,p.user);
}
}
void input_mouse_cleanup(InputMouseLifetimeState& state,const InputMouseLifetimePlatform& p){
    using namespace mouse_lifetime_call;auto& w=state.words;
    if(w[12]){call(state,p,unacquire,w[12]);call(state,p,release,w[12]);w[12]=0;}
    if(w[11]){call(state,p,release,w[11]);w[11]=0;}
}
void input_mouse_bounds(InputMouseLifetimeState& state,const InputMouseLifetimePlatform& p,
                        std::span<const std::uint32_t,6> a){
    auto& w=state.words;w[10]=a[2];w[8]=a[0];w[9]=a[1];w[1]=a[3];w[2]=a[4];w[0]=a[5];
    call(state,p,0x6f0720,0,{a[0],a[1],a[3],a[4]});
}
std::uint32_t input_mouse_lifetime(InputMouseLifetimeState& state,const InputMouseLifetimePlatform& p,
                                   std::uint32_t temporary){
    using namespace mouse_lifetime_call;auto& w=state.words;
    if(w[13]==0){w[13]=1;call(state,p,0x6f06c0);call(state,p,0x582e40,0,{0x20a,0x6efa60});}
    if(w[11]==0){
        const auto module_id=call(state,p,module,0,{0});
        auto status=call(state,p,create,0,{module_id,0x500,0},1,{&w[11],1});
        if(status==0){
            status=call(state,p,create_device,w[11],{0x84c950,0},2,{&temporary,1});
            if(status==0){
                status=call(state,p,query,temporary,{0x84ca70},3,{&w[12],1});
                call(state,p,release,temporary);
                if(status==0){
                    status=call(state,p,format,w[12],{0x84b720});
                    if(status==0)status=call(state,p,property,w[12],{2,0x14,0x10,0,0,1});
                }
            }
        }
        if(status!=0)input_mouse_cleanup(state,p);
    }
    w[3]=2;w[4]=0;w[5]=0;w[6]=0;w[7]=0;
    call(state,p,0x6efaf0,0,{8,2});call(state,p,0x6efaf0,0,{9,1});
    const std::array<std::uint32_t,6> bounds{0,0,0,state.width,state.height,0x4b0};
    input_mouse_bounds(state,p,bounds);
    if(w[11]!=0)call(state,p,0x6efaf0,0,{7,4});
    if(w[14]==0){call(state,p,0x6bf450,0,{0x6efad0});w[14]=1;}
    // Supported bridge domain writes both POINT words, including failed queries.
    std::array<std::uint32_t,2> point{};
    call(state,p,cursor,0,{},4,point);
    const auto window=call(state,p,0x584cf0);
    if(call(state,p,client,0,{window},4,point)!=0){
        call(state,p,0x6efaf0,0,{3,point[0]});call(state,p,0x6efaf0,0,{4,point[1]});
    }
    return w[13];
}
}
