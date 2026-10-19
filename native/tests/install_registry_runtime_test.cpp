#include "mco/install_registry_runtime.hpp"
#include <array>
#include <stdexcept>
static std::uint32_t fail(mco::RegistryInstallState&,std::uint32_t,std::span<const std::uint32_t>,std::span<std::byte>,void*){return 5;}
int main(){std::array<std::byte,0x210> bytes{};mco::RegistryInstallState state{bytes,0x1234};if(mco::registry_install_is_open(state))return 1;bytes[7]=std::byte{0x80};if(!mco::registry_install_is_open(state))return 2;bool rejected=false;try{mco::registry_install_language(state,{fail,nullptr});}catch(const std::invalid_argument&){rejected=true;}if(!rejected||state.language!=0x1234)return 3;const auto before=bytes;bool bridge=false;try{mco::registry_install_reopen(state,{},0x80000002,0x71001000,0xf003f);}catch(const std::invalid_argument&){bridge=true;}return bridge&&before==bytes?0:4;}
