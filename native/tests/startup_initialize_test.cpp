#include "startup_initialize_cases.hpp"
#include <algorithm>
using namespace mco;
void require(bool v){if(!v)throw std::runtime_error("startup invariant");}
int main(){
    queue_cases::Fixture queue;auto q=queue.state();startup_initialize_cases::Fixture f;StartupState state{q,f.values};using G=StartupGlobal;
    state.at(G::diagnostic_callback)=startup_initialize_cases::diag0;state.at(G::auxiliary_ready)=1;
    f.config={0,0,0,0,0,0};startup_initialize(state,f.platform());
    require(state.at(G::driver_name)==0x896bc0 && state.at(G::driver_loaded)==1);
    require(state.at(G::diagnostic_line)==0x6a);
    require(std::none_of(f.logs.begin(),f.logs.end(),[](const auto& row){return row[0]==0x6f0200;}));
    f.logs.clear();state.at(G::graphics_ready)=1;state.at(G::width)=640;state.at(G::height)=480;
    startup_initialize(state,f.platform());
    require(q.load(input_queue_image::policy_enabled)==1 && q.load(input_queue_image::policy_flag)==1);
    require(state.at(G::policy_callback)==0x6bfc60);
    const auto& viewport=f.logs.back();require(viewport[0]==0x6cb610 && viewport[4]==0x44200000 && viewport[5]==0x43f00000);
    auto at=[&](std::uint32_t id){return std::find_if(f.logs.begin(),f.logs.end(),[&](const auto& row){return row[0]==id;});};
    require(at(0x6f0200)<at(0x6f09f0) && at(0x6f09f0)<at(0x6f0360));
    startup_window_policy(state,0xffffffff,0);require(q.load(input_queue_image::policy_enabled)==1 && q.load(input_queue_image::policy_flag)==0xffffffff && state.at(G::policy_callback)==0);
}
