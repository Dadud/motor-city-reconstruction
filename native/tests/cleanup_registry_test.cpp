#include "mco/cleanup_registry.hpp"
#include <array>
#include <stdexcept>
#include <vector>
using namespace mco;
void require(bool v) {if(!v)throw std::runtime_error("cleanup registry invariant");}
int main() {
    std::array<std::uint32_t,64> slots{};CleanupRegistry state{slots};
    cleanup_registry_register(state,0);require(slots[0]==0);
    cleanup_registry_register(state,17);cleanup_registry_register(state,17);
    require(slots[0]==17 && slots[1]==0);
    slots.fill(19);cleanup_registry_register(state,23);require(slots[63]==19);
    slots.fill(0);slots[63]=1;slots[4]=2;
    std::vector<std::uint32_t> calls;
    CleanupRegistryPlatform platform{[](CleanupRegistry& s,std::uint32_t id,void* user){
        static_cast<std::vector<std::uint32_t>*>(user)->push_back(id);
        if(id==1){s.slots[63]=9;s.slots[4]=3;s.slots[0]=4;}
        if(id==3)s.slots[63]=5;
    },&calls};
    cleanup_registry_run(state,platform);
    require(calls==std::vector<std::uint32_t>{1,3,4});
    require(slots[63]==5 && slots[4]==0 && slots[0]==0);
    cleanup_registry_run(state,platform);require(calls.back()==5 && slots[63]==0);
    cleanup_registry_run(state,{});
}
