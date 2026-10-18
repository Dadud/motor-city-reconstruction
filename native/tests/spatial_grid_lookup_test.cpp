#include "mco/spatial_grid_lookup.hpp"
#include <array>
#include <cfenv>
#include <stdexcept>
int main() {
    std::array<std::byte,65536> grid{};
    std::array<std::byte,32> nodes{};
    unsigned diagnostics=0;
    mco::SpatialQueryMemory memory{grid,nodes,0x71001000,
        [](std::uint32_t id,void* user) {
            if(id!=0x89900c) throw std::runtime_error("diagnostic identity changed");
            ++*static_cast<unsigned*>(user);
        },&diagnostics};
    std::array<float,3> position{0.5f,77,0};
    std::array<float,2> origin{0,0},scale{1,1};
    mco::detail::write_word(grid,0,0xdeadbeef);
    if(mco::spatial_grid_lookup(memory,position,origin,scale)!=memory.grid_address)
        throw std::runtime_error("half-even root lookup changed");
    position[0]=-1;
    if(mco::spatial_grid_lookup(memory,position,origin,scale)!=0)
        throw std::runtime_error("outside coordinate accepted");
    position[0]=512;
    mco::detail::write_word(grid,0,0);
    mco::detail::write_word(grid,4,0x71001000);
    mco::detail::write_word(nodes,0,0xdeadbeef);
    if(mco::spatial_grid_lookup(memory,position,origin,scale)!=0x71001000)
        throw std::runtime_error("quadrant ordering changed");
    mco::detail::write_word(nodes,0,0x71001010);
    mco::detail::write_word(nodes,16,0);
    if(mco::spatial_grid_lookup(memory,position,origin,scale)!=0 || diagnostics!=1)
        throw std::runtime_error("corrupt depth diagnostic changed");
    mco::detail::write_word(grid,4,0x12345678);
    bool rejected=false;
    try {mco::spatial_grid_lookup(memory,position,origin,scale);}
    catch(const std::invalid_argument&) {rejected=true;}
    if(!rejected) throw std::runtime_error("unmapped node accepted");
    const auto previous=std::fegetround();
    std::fesetround(FE_DOWNWARD);
    rejected=false;
    try {mco::spatial_grid_lookup(memory,position,origin,scale);}
    catch(const std::invalid_argument&) {rejected=true;}
    std::fesetround(previous);
    if(!rejected) throw std::runtime_error("unsupported rounding accepted");
}
