#include "mco/mechanical_loaders.hpp"
#include <stdexcept>
int main() {
    const std::array<std::byte,0x820> config{};
    const std::array<std::byte,0x984> part{};
    for(auto kind:{160001U,130001U,140001U,100001U,12001U,11001U,10001U,
            1000001U,1100001U,1200001U,180001U,190001U,200001U}) {
        const auto out=mco::load_mechanical_component(kind,config,part);
        if(out.status!=1 || out.configuration!=config || out.component!=part)
            throw std::runtime_error("mechanical count rejection must preserve images");
    }
    bool rejected=false;
    try {mco::load_mechanical_component(999,config,part);}
    catch(const std::invalid_argument&) {rejected=true;}
    if(!rejected) throw std::runtime_error("unknown mechanical loader accepted");
    rejected=false;
    try {mco::load_mechanical_component(160001,{},part);}
    catch(const std::invalid_argument&) {rejected=true;}
    if(!rejected) throw std::runtime_error("short mechanical image accepted");
}
