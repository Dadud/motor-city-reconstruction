#include "mco/installation_support.hpp"
#include <stdexcept>
int main(){
 if(mco::installation_path_address(0xffffffffu)!=0xa52c44u)return 1;
 if(mco::installation_cd_mode(0x80000100)!=0x80000100)return 2;
 bool rejected=false;try{mco::installation_drive_is_cd(0,{});}catch(const std::invalid_argument&){rejected=true;}
 return rejected?0:3;
}
