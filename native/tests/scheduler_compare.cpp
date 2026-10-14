#include "mco/scheduler.hpp"
#include <iostream>
#include <vector>
int main() {
    for(int count=0;count<100000;++count) {
        std::uint32_t counter,clock,processed; std::int32_t frame,mode; int enabled,inhibited;
        if(!(std::cin>>counter>>frame>>enabled>>mode>>inhibited>>clock>>processed)) return std::cin.eof()?0:2;
        std::vector<int> calls;
        const auto repetitions=mco::selected_iterations(enabled!=0,mode,frame);
        const auto result=mco::execute_batch(counter,repetitions,inhibited!=0,
            [&]{calls.push_back(1);},[&]{calls.push_back(2);},[&]{calls.push_back(3);});
        std::cout<<result<<' '<<repetitions<<' '<<calls.size();
        for(auto call:calls) std::cout<<' '<<call;
        std::cout<<' '<<mco::pending_iterations(clock,processed);
        std::cout<<'\n';
    }
    return 2;
}
