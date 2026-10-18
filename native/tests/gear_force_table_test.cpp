#include "mco/gear_force_table.hpp"
#include <array>
#include <stdexcept>
int main() {
    bool rejected=false;try{mco::gear_force_table({}, {},0);}catch(const std::invalid_argument&){rejected=true;}
    if(!rejected)throw std::runtime_error("incomplete configuration accepted");
    std::array<std::byte,0x820> c{};
    rejected=false;try{mco::gear_force_table(c,{},8);}catch(const std::invalid_argument&){rejected=true;}
    if(!rejected)throw std::runtime_error("invalid selector accepted");
    rejected=false;try{mco::gear_force_table(c,{},0);}catch(const std::invalid_argument&){rejected=true;}
    if(!rejected)throw std::runtime_error("zero tire radius accepted");
}
