#include "mco/world_object_array.hpp"
#include <iostream>

int main() {
    std::uint32_t base{};
    std::size_t count{};
    while (std::cin>>base>>count) {
        std::vector<bool> active(count);
        for (std::size_t index=0;index<count;++index) {
            int value{};
            if (!(std::cin>>value)) return 2;
            active[index]=value!=0;
        }
        mco::update_active_world_objects(base,active,[](auto address){std::cout<<address<<' ';});
        std::cout<<'\n';
    }
}
