#pragma once
#include "mco/installation_support.hpp"
#include "cell_io.hpp"
#include <vector>
namespace installation_support_cases {
struct Boundary {std::uint32_t result;std::vector<std::uint32_t> path;};
inline std::uint32_t query(std::span<const std::byte,4> path,void* user){
 auto& b=*static_cast<Boundary*>(user);for(auto x:path)b.path.push_back(std::uint32_t(x));return b.result;
}
inline void compare(std::istream& in){
 using namespace cell_io;const auto mode=read(in),value=read(in);Boundary b{read(in),{}};
 std::uint32_t result=0;
 switch(mode){case 0:result=mco::installation_drive_is_cd(value,{query,&b});break;
 case 1:result=mco::installation_path_address(value);break;
 case 2:result=mco::installation_cd_mode(value);break;
 default:throw std::invalid_argument("installation support operation");}
 emit(result);for(auto x:b.path)emit(x);
}
}
