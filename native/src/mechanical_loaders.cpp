#include "mco/mechanical_loaders.hpp"
#include <algorithm>
#include <bit>
#include <cmath>
#include <limits>
#include <stdexcept>
namespace mco {
namespace {
std::uint32_t word(std::span<const std::byte> image,std::size_t offset) {
    std::uint32_t value=0;
    for(unsigned i=0;i<4;++i) value|=std::to_integer<std::uint32_t>(image[offset+i])<<(i*8);
    return value;
}
void put_word(std::span<std::byte> image,std::size_t offset,std::uint32_t value) {
    for(unsigned i=0;i<4;++i) image[offset+i]=static_cast<std::byte>((value>>(i*8))&255);
}
double finite(double v) {
    if(!std::isfinite(v)) throw std::invalid_argument("finite mechanical observation required");
    return v;
}
std::int32_t nearest(double v) {
    const double lower=std::floor(v),fraction=v-lower;
    const double value=lower+(fraction>.5 || (fraction==.5 && std::fmod(lower,2.)!=0));
    if(value<std::numeric_limits<std::int32_t>::min() || value>std::numeric_limits<std::int32_t>::max())
        return std::numeric_limits<std::int32_t>::min();
    return static_cast<std::int32_t>(value);
}
std::int32_t truncated(double v) {
    v=std::trunc(v);
    if(v < -9223372036854775808. || v>=9223372036854775808.) return 0;
    double remainder=std::fmod(v,4294967296.);
    if(remainder>=2147483648.) remainder-=4294967296.;
    if(remainder< -2147483648.) remainder+=4294967296.;
    return static_cast<std::int32_t>(remainder);
}
struct Image {
    ComponentLoadResult original,out;
    Image(std::span<const std::byte> config,std::span<const std::byte> component) {
        if(config.size()!=0x820 || component.size()!=0x984)
            throw std::invalid_argument("expected mechanical configuration and component images");
        original.status=0;
        std::copy(config.begin(),config.end(),original.configuration.begin());
        std::copy(component.begin(),component.end(),original.component.begin());
        out=original;
    }
    double number(std::size_t offset) const {
        return finite(std::bit_cast<float>(word(out.component,offset)));
    }
    double existing(std::size_t offset) const {
        return finite(std::bit_cast<float>(word(out.configuration,offset)));
    }
    void put(std::size_t offset,double value) {
        if(!std::isfinite(value) || std::abs(value)>std::numeric_limits<float>::max())
            throw std::invalid_argument("finite mechanical result required");
        put_word(out.configuration,offset,std::bit_cast<std::uint32_t>(static_cast<float>(value)));
    }
    void integer(std::size_t offset,std::int32_t value) {
        put_word(out.configuration,offset,std::bit_cast<std::uint32_t>(value));
    }
    void copy(std::size_t destination,std::size_t source,std::size_t size=4) {
        std::copy_n(out.component.begin()+source,size,out.configuration.begin()+destination);
    }
    void quality_value(double v) {
        put_word(out.component,0x1c,std::bit_cast<std::uint32_t>(static_cast<float>(v)));
    }
    void quality() {
        const auto duty=nearest(number(0x34));
        quality_value(duty==0 ? .75 : duty==2 ? 2. : duty==3 ? 4. : 1.);
    }
    void add_mass() {put(0x20,existing(0x20)+number(0x30));}
    void add_mass(double unsprung) {add_mass();put(0x28,existing(0x28)+number(0x30)*unsprung);}
    std::uint32_t count() const {return word(out.component,0x14)&0x3fffffffU;}
    bool front() const {const auto a=word(out.component,0x18);return a==1 || a==2;}
    bool bounded(std::size_t offset,float low,float high) const {const auto v=number(offset);return v>=low && v<=high;}
    bool rounded_between(std::size_t offset,int low,int high) const {const auto v=nearest(number(offset));return v>=low && v<=high;}
    ComponentLoadResult fail(std::uint32_t status) const {auto result=original;result.status=status;return result;}
};
ComponentLoadResult engine(Image& m) {
    if(m.count()!=7) return m.fail(1);
    for(auto offset:{0x30,0x34,0x3c,0x40,0x44,0x48,0x4c,0x50,0x54})
        if(!std::isfinite(std::bit_cast<float>(word(m.out.component,offset)))) return m.fail(2);
    const auto family=word(m.out.component,0x53b);
    const auto material=truncated(m.number(0x50));
    if(!(m.bounded(0x30,30.f,200.f) && m.bounded(0x3c,.0508f,.127f) &&
        m.bounded(0x40,.0635f,.127f) && m.bounded(0x44,3.f,10.f) &&
        m.bounded(0x54,5.f,40.f) && m.rounded_between(0x48,6,8) &&
        family>=1 && family<=26 && m.rounded_between(0x50,0,9) &&
        material!=4 && material!=5 && material!=6 && material!=7 && material!=9)) return m.fail(2);
    constexpr std::array<std::size_t,6> destinations{0x450,0x459,0x45d,0x461,0x465,0x469};
    std::array<std::size_t,6> lengths{};
    for(std::size_t i=0;i<6;++i) {
        const auto begin=m.out.component.begin()+0x120+i*32;
        const auto end=std::find(begin,begin+32,std::byte{0});
        if(end==begin+32) throw std::invalid_argument("engine block text requires a bounded terminator");
        lengths[i]=static_cast<std::size_t>(end-begin)+1;
    }
    m.add_mass();
    for(auto pair:std::array<std::array<std::size_t,2>,6>{{{0x428,0x30},{0x430,0x3c},{0x434,0x40},
            {0x438,0x44},{0x440,0x53b},{0x44c,0x54}}}) m.copy(pair[0],pair[1]);
    m.integer(0x42c,truncated(m.number(0x34)));m.integer(0x43c,truncated(m.number(0x48)));
    m.integer(0x444,material);
    for(std::size_t i=0;i<6;++i) m.copy(destinations[i],0x120+i*32,lengths[i]);
    put_word(m.out.configuration,0x7c,word(m.out.configuration,0x43c));
    put_word(m.out.configuration,0x74,word(m.out.configuration,0x438));
    m.integer(0x6c,500);m.integer(0x70,7000);m.put(0x448,1.);
    std::fill(m.out.configuration.begin()+0x80,m.out.configuration.begin()+0xe4,std::byte{0});
    constexpr std::array<float,8> quality{1.f,1.05f,.96f,.97f,1.1f,1.4f,1.75f,2.f};
    m.quality_value(material>=0 && material<=7 ? quality[material] : 1.f);
    return m.out;
}
ComponentLoadResult transmission(Image& m) {
    if(m.count()!=19) return m.fail(1);
    bool valid=m.bounded(0x30,20.f,100.f) && m.rounded_between(0x3c,0,1) &&
        m.rounded_between(0x44,4,64) && m.rounded_between(0x40,4,8) && m.rounded_between(0x34,0,3);
    int populated=1;
    for(std::size_t i=0;i<8;++i) {
        const double ratio=m.number(0x48+i*4),loss=m.number(0x68+i*4);
        if(ratio!=0) ++populated;
        if(ratio>=5 || loss>1) valid=false;
    }
    if(!valid || populated!=truncated(m.number(0x40))) return m.fail(2);
    m.add_mass();m.copy(0x680,0x30);
    for(auto pair:std::array<std::array<std::size_t,2>,6>{{{0x684,0x34},{0x68c,0x3c},{0x690,0x40},
            {0x694,0x44},{0x32c,0x40},{0x330,0x44}}}) m.integer(pair[0],nearest(m.number(pair[1])));
    m.put(0x688,(nearest(m.number(0x34))+1)*250.);
    for(auto pair:std::array<std::array<std::size_t,2>,4>{{{0x698,0x48},{0x6b8,0x68},{0x334,0x48},{0x354,0x68}}}) m.copy(pair[0],pair[1],32);
    m.quality();return m.out;
}
ComponentLoadResult rear_end(Image& m) {
    if(m.count()!=3) return m.fail(1);
    if(!(m.bounded(0x30,18.f,50.f) && m.rounded_between(0x40,0,1) &&
        m.bounded(0x3c,2.5f,6.f) && m.bounded(0x44,.9f,1.f) && m.rounded_between(0x34,0,3))) return m.fail(2);
    m.add_mass();m.copy(0x6d8,0x30);m.copy(0x6e4,0x3c);m.copy(0x6e8,0x44);m.copy(0x374,0x3c);
    m.integer(0x6ec,nearest(m.number(0x40)));m.integer(0x6dc,nearest(m.number(0x34)));
    const int duty=nearest(m.number(0x34))+1;m.put(0x6e0,duty*duty*100.+650.);
    m.quality();return m.out;
}
ComponentLoadResult rim(Image& m) {
    if(m.count()!=1) return m.fail(1);
    if(!(m.bounded(0x30,5.f,75.f) && m.rounded_between(0x3c,0,9) && truncated(m.number(0x3c))!=9)) return m.fail(2);
    m.add_mass(1.);const auto base=m.front() ? 0x700 : 0x70c;
    m.copy(base,0x30);m.integer(base+4,nearest(m.number(0x34)));m.integer(base+8,nearest(m.number(0x3c)));
    m.quality();return m.out;
}
ComponentLoadResult spring(Image& m) {
    if(m.count()!=2) return m.fail(1);
    if(!(m.bounded(0x30,2.f,30.f) && m.bounded(0x3c,10000.f,120000.f) &&
        m.rounded_between(0x34,0,3) && m.rounded_between(0x40,0,3))) return m.fail(2);
    m.add_mass(.5);const auto base=m.front() ? 0x628 : 0x638;
    m.copy(base,0x30);m.integer(base+4,truncated(m.number(0x34)));m.copy(base+8,0x3c);m.integer(base+12,truncated(m.number(0x40)));
    const auto attachment=word(m.out.component,0x18);
    if(attachment==1 || attachment==3) {
        const double arm=m.existing(attachment==1 ? 0x30 : 0x34)*static_cast<double>(attachment==1 ? .76f : .68f);
        const auto target=attachment==1 ? 0xfc : 0x104;
        m.put(target,((arm*m.number(0x3c))*arm)*static_cast<double>(.0087265f)+m.existing(target));
    }
    return m.out;
}
ComponentLoadResult shock(Image& m) {
    if(m.count()!=2) return m.fail(1);
    if(!(m.bounded(0x30,2.f,10.f) && m.rounded_between(0x34,0,3) &&
        m.bounded(0x3c,.2f,.4f) && m.bounded(0x40,.1016f,.4064f))) return m.fail(2);
    m.add_mass(.5);const auto base=m.front() ? 0x608 : 0x618;
    m.copy(base,0x30);m.integer(base+4,truncated(m.number(0x34)));m.copy(base+8,0x3c);m.copy(base+12,0x40);
    m.quality();return m.out;
}
ComponentLoadResult brake(Image& m) {
    if(m.count()!=5) return m.fail(1);
    if(!(m.bounded(0x30,2.f,20.f) && m.rounded_between(0x3c,0,1) && m.rounded_between(0x40,0,3) &&
        m.rounded_between(0x44,0,20) && m.bounded(0x48,.0254f,.1016f) &&
        m.rounded_between(0x4c,0,1) && m.rounded_between(0x34,0,3))) return m.fail(2);
    const double mass=std::max(4.,m.number(0x30));
    m.put(0x20,m.existing(0x20)+mass);m.put(0x28,m.existing(0x28)+mass);
    const auto base=m.front() ? 0x5c8 : 0x5e8;
    m.copy(base,0x30);
    for(auto pair:std::array<std::array<std::size_t,2>,5>{{{4,0x34},{8,0x3c},{12,0x40},{16,0x44},{24,0x4c}}}) m.integer(base+pair[0],truncated(m.number(pair[1])));
    m.copy(base+20,0x48);const auto material=truncated(m.number(0x40));
    m.put(base+28,material==1 ? 300. : material==2 ? 375. : material==3 ? 450. : 225.);
    m.quality_value(material==0 ? .8f : material==2 ? 1.5f : material==3 ? 2.f : 1.f);
    return m.out;
}
}
ComponentLoadResult load_mechanical_component(std::uint32_t kind,
    std::span<const std::byte> config,std::span<const std::byte> component) {
    Image image(config,component);
    switch(kind) {
        case 160001:return engine(image);
        case 130001:return transmission(image);
        case 140001:return rear_end(image);
        case 100001:return rim(image);
        case 12001:return spring(image);
        case 11001:return shock(image);
        case 10001:return brake(image);
        default:throw std::invalid_argument("unrecovered mechanical component loader");
    }
}
}
