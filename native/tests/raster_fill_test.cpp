#include "mco/raster_fill.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cstddef>

int main() {
    const auto mask=mco::rasterize_projected_triangle(
        {{{{1,1}},{{9,1}},{{5,9}}}},0,10,0,10);
    std::size_t count=0;
    int min_x=321,min_y=241,max_x=-1,max_y=-1;
    for(std::size_t i=0;i<mask.size();++i) if(mask[i]) {
        ++count;
        const auto x=static_cast<int>(i%321), y=static_cast<int>(i/321);
        if(x<min_x) min_x=x;
        if(x>max_x) max_x=x;
        if(y<min_y) min_y=y;
        if(y>max_y) max_y=y;
    }
    assert(count==24769);
    assert(min_x==32 && min_y==24 && max_x==288 && max_y==216);
}
