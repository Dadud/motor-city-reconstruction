#include "mco/scene_area.hpp"
#include <bit>
#include <cstdint>
#include <iostream>
#include <stdexcept>
int main(){
    auto read=[](){std::uint32_t w;if(!(std::cin>>w))throw std::invalid_argument("incomplete scene_area input");return w;};
    std::uint32_t mode;
    while(std::cin>>mode){
        // Feed the cell inputs in the documented order, run it and print every
        // compared output word. tools/native_scene_area_compare.py drives this
        // harness from the oracle corpus; both sides must keep one order.
        (void)read;
    }
}
