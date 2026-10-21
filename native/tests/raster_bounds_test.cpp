#include "mco/raster_bounds.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <array>
#include <cassert>
#include <stdexcept>
#include <vector>

int main() {
    constexpr std::size_t size=0x141u*0xf1u;
    std::vector<std::uint8_t> bitmap(size);
    auto bounds=mco::occupied_raster_bounds(bitmap);
    assert((bounds.min_x==1'000'000 && bounds.min_y==1'000'000 &&
            bounds.max_x==-1'000'000 && bounds.max_y==-1'000'000 && bounds.count==0));
    bitmap[0]=1;bitmap[320]=0xff;bitmap[240*321]=2;bitmap.back()=3;
    bounds=mco::occupied_raster_bounds(bitmap);
    assert((bounds.min_x==0 && bounds.min_y==0 && bounds.max_x==320 &&
            bounds.max_y==240 && bounds.count==4));
    bool rejected=false;
    try { mco::occupied_raster_bounds(std::span<const std::uint8_t>(bitmap.data(),bitmap.size()-1)); }
    catch(const std::invalid_argument&) { rejected=true; }
    assert(rejected);
}
