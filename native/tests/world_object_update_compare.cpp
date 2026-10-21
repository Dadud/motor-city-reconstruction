#include "mco/world_object_update.hpp"
#include <bit>
#include <iomanip>
#include <iostream>

template <std::size_t N>
bool read_values(std::array<float,N>& values) {
    for(auto& value:values) if(!(std::cin>>value)) return false;
    return true;
}

int main() {
    std::uint32_t object_id{},phase{};
    int active{};
    while(std::cin>>object_id>>active>>phase) {
        mco::WorldObjectUpdate state{};
        state.object_id=object_id; state.active=active!=0;
        if(!read_values(state.position)||!read_values(state.linear_velocity)||
           !read_values(state.center_of_mass)||!read_values(state.rotation)||
           !read_values(state.angular_velocity)||!read_values(state.projection_vector)||
           !read_values(state.local_vertices)) return 2;
        state=mco::update_world_object(state,phase);
        for(const auto value:state.position) std::cout<<std::hex<<std::bit_cast<std::uint32_t>(value)<<' ';
        for(const auto value:state.rotation) std::cout<<std::hex<<std::bit_cast<std::uint32_t>(value)<<' ';
        for(const auto value:state.transposed_rotation) std::cout<<std::hex<<std::bit_cast<std::uint32_t>(value)<<' ';
        for(const auto value:state.projected) std::cout<<std::hex<<std::bit_cast<std::uint32_t>(value)<<' ';
        for(const auto value:state.world_vertices) std::cout<<std::hex<<std::bit_cast<std::uint32_t>(value)<<' ';
        std::cout<<'\n';
    }
}
