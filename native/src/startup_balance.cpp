#include "mco/startup_balance.hpp"
#include "mco/tire_response.hpp"
#include <algorithm>
#include <bit>
#include <cmath>
#include <cstdint>
#include <stdexcept>
namespace mco {
namespace {
double rounded(double value) {const auto result=static_cast<float>(value);if(!std::isfinite(result)) throw std::invalid_argument("finite startup coefficient required");return result;}
double number(std::span<const std::byte> config,unsigned offset) {
    if(config.size()!=0x820) throw std::invalid_argument("complete configuration image required");
    std::uint32_t word=0;for(unsigned k=0;k<4;++k) word|=std::to_integer<std::uint32_t>(config[offset+k])<<(k*8);
    const auto value=std::bit_cast<float>(word);if(!std::isfinite(value)) throw std::invalid_argument("finite configuration observations required");return value;
}
}
float startup_load_coefficient(std::span<const std::byte> config) {
    auto n=[&](unsigned offset){return number(config,offset);};
    const auto mass=n(0x20)-n(0x28),height=n(0x38);
    const auto denominator=(n(0x104)+n(0xfc))-height*.3181818127632141f*mass*.17121680080890656f;
    if(denominator==0) throw std::invalid_argument("nonzero startup load denominator required");
    return static_cast<float>(rounded((height*.9090908765792847f*mass*9.8100004196167f)/denominator));
}
float startup_balance_coefficient(std::span<const std::byte> config,bool alternate) {
    auto n=[&](unsigned offset){return number(config,offset);};
    for(auto offset:{0x2c,0x30,0x34,0x144,0x248}) if(n(offset)<=0)
        throw std::invalid_argument("positive wheelbase tracks and template widths required");
    const double coefficient=startup_load_coefficient(config),wheelbase=n(0x2c);
    const auto angle=rounded(std::atan2(wheelbase,33.)*.15915493667125702),angle_scale=angle*360.;
    if(angle_scale==0) throw std::invalid_argument("nonzero angular scale required");
    struct Axle {double displacement,correction,secondary;};
    auto axle=[&](bool front) {
        const auto lever=rounded(front?wheelbase*n(0x3c):(1.-n(0x3c))*wheelbase);
        const auto weight=rounded(((n(0x20)*4.90500020980835f)/wheelbase)*lever);
        const auto ratio=rounded(n(front?0x124:0x228)/n(front?0x144:0x248));
        const auto surface=std::clamp(ratio,static_cast<double>(.9f),1.5);
        const WheelCurveInput input{angle,0.,weight,surface};WheelResponseTable primary{},secondary{};
        for(unsigned i=0;i<26;++i) {primary[i]=n((front?0x150:0x254)+i*4);secondary[i]=n((front?0x1b8:0x2bc)+i*4);}
        const auto stiffness=rounded(wheel_response(primary,n(front?0x148:0x24c),input,false,alternate)/angle_scale);
        const auto secondary_stiffness=rounded(wheel_response(secondary,n(front?0x148:0x24c),input,true)/angle_scale);
        if(stiffness==0) throw std::invalid_argument("nonzero primary response stiffness required");
        // This intermediate remains in x87 registers in the original function.
        const auto transfer=((coefficient*n(front?0xfc:0x104)+(weight+weight)*n(0x38)*.45454543828964233f)*.29876917600631714f)/n(front?0x30:0x34);
        const auto displacement=rounded(weight/stiffness);
        const auto correction=rounded(((transfer*transfer*9.705000411486253e-05f)/stiffness)*displacement);
        return Axle{displacement,correction,secondary_stiffness};
    };
    const auto front=axle(true),rear=axle(false);double extra=0;
    if(front.secondary!=0 && rear.secondary!=0)
        extra=rounded(std::abs((9.8100004196167f/wheelbase)*((rear.secondary+front.secondary)/(rear.secondary*front.secondary))));
    const auto value=rounded((front.correction-rear.correction)+(front.displacement-rear.displacement)+extra);
    return static_cast<float>(std::clamp(value,-10.,10.));
}

float brake_diameter(std::uint32_t code) {
    constexpr std::uint32_t values[]{1045435305,1046287588,1047139870,1047992153,1048710218,
        1049136359,1049562500,1049988641,1050414783,1050840924,1051267065,1051693207,
        1052119348,1052545489,1052971630,1053397772,1053823913,1054250054,1054676196,1055102337,1055528478};
    return std::bit_cast<float>(values[code<=20?code:0]);
}
double brake_capacity(float diameter,std::uint32_t material,std::uint32_t construction,float pressure,bool auxiliary) {
    if(!std::isfinite(diameter) || !std::isfinite(pressure)) throw std::invalid_argument("finite brake capacity inputs required");
    const double factor=material==0?.85f:material==1?.9f:material==2?.95f:1.;
    const double radius=static_cast<double>(diameter)*.5;
    auto result=radius*radius*3.1415927410125732f*16.31012725830078f*2500.*factor*pressure;
    if(construction==1) {result*=.98f;if(auxiliary) result*=.8f;}
    if(!std::isfinite(result)) throw std::invalid_argument("finite brake capacity required");return result;
}
float startup_brake_balance(std::span<const std::byte> config) {
    auto n=[&](unsigned offset){return number(config,offset);};
    auto word=[&](unsigned offset) {std::uint32_t value=0;for(unsigned k=0;k<4;++k) value|=std::to_integer<std::uint32_t>(config[offset+k])<<(k*8);return value;};
    const auto wheelbase=n(0x2c);if(wheelbase<=0) throw std::invalid_argument("positive wheelbase required");
    const auto mass_force=rounded(n(0x20)*9.8100004196167f);
    const auto per_length=(n(0x20)*9.8100004196167f)/wheelbase;
    const auto front=rounded(wheelbase*n(0x3c)*per_length),rear=rounded((1.-n(0x3c))*wheelbase*per_length);
    const auto height=rounded(n(0x38)*.9090908765792847f);
    auto capacity=[&](bool front) {const auto offset=front?0x5d0:0x5f0;return brake_capacity(brake_diameter(word(offset+8)),word(offset+4),word(offset),1.f,false);};
    auto radius=[&](bool front) {const auto offset=front?0x124:0x228;
        const auto sidewall=(n(offset)*.001f)*(n(offset+4)*.01f);
        const auto value=(sidewall+sidewall+n(offset+8)*.0254f)*.5;
        if(value<=0) throw std::invalid_argument("positive tire radius required");return value;
    };
    const auto front_capacity=rounded(capacity(true)/radius(true));
    if(front_capacity==0) throw std::invalid_argument("nonzero front brake capacity required");
    const auto ratio=std::clamp(rounded((capacity(false)/radius(false))/front_capacity),.5,1.);
    const auto front_mu=n(0x140),rear_mu=n(0x244);
    const auto rear_transfer=rounded((height/wheelbase)*rear_mu),rear_remaining=rounded(1.-rear_transfer);
    const auto front_transfer=(height/wheelbase)*front_mu,front_remaining=1.-front_transfer;
    if(front_remaining==0 || rear_remaining==0) throw std::invalid_argument("nonzero brake transfer denominators required");
    const auto numerator=(rear_mu*rear)/rear_remaining-(front_transfer/front_remaining)*((front_mu*height*mass_force)/wheelbase+front)*front_mu;
    const auto denominator=(front_mu*front)/front_remaining+(rear_transfer/rear_remaining)*(rear-(rear_mu*height*mass_force)/wheelbase)*rear_mu;
    if(denominator==0) throw std::invalid_argument("nonzero brake balance denominator required");
    return static_cast<float>(std::clamp(rounded((numerator/denominator)/ratio),static_cast<double>(.1f),1.));
}
}
