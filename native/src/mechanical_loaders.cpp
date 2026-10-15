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
bool same_engine_family(const Image& m) {
    const auto family=word(m.out.component,0x53b);
    return family!=0 && family==word(m.out.configuration,0x440);
}
void material_quality(Image& m,std::size_t offset,bool head=false) {
    constexpr std::array<float,9> standard{1.f,1.04f,.95f,.96f,1.2f,1.5f,1.65f,3.f,.93f};
    constexpr std::array<float,8> heads{1.f,1.05f,.96f,.97f,1.1f,1.4f,1.75f,2.f};
    const auto i=nearest(m.number(offset));
    m.quality_value(head ? (i>=0 && i<8 ? heads[i] : 1.f) : (i>=0 && i<9 ? standard[i] : 1.f));
}
void cylinder_mass(Image& m,std::size_t individual,std::size_t total) {
    const auto count=std::bit_cast<std::int32_t>(word(m.out.configuration,0x43c));
    const double product=count*m.number(0x30);
    m.copy(individual,0x30);m.put(total,product);
    // Original FST does not pop: addition uses the unrounded product.
    m.put(0x20,m.existing(0x20)+product);
}
ComponentLoadResult cylinder_head(Image& m) {
    if(m.count()!=7) return m.fail(1);
    const auto material=truncated(m.number(0x40));
    if(!(same_engine_family(m) && m.bounded(0x30,10.f,80.f) &&
        m.rounded_between(0x3c,0,2) && m.rounded_between(0x40,0,9) &&
        material!=8 && material!=9 && m.rounded_between(0x44,0,5) &&
        m.bounded(0x48,.97f,1.03f) && m.bounded(0x4c,6.f,20.f) &&
        m.bounded(0x50,25.4f,63.5f) && m.bounded(0x54,25.4f,50.8f) &&
        word(m.out.component,0x53b)<=26)) return m.fail(2);
    m.add_mass();
    for(auto p:std::array<std::array<std::size_t,2>,7>{{{0x504,0x30},{0x518,0x48},
        {0x51c,0x4c},{0x54,0x4c},{0x520,0x53b},{0x524,0x50},{0x528,0x54}}}) m.copy(p[0],p[1]);
    for(auto p:std::array<std::array<std::size_t,2>,4>{{{0x508,0x34},{0x50c,0x3c},
        {0x510,0x44},{0x514,0x40}}}) m.integer(p[0],nearest(m.number(p[1])));
    material_quality(m,0x40,true);return m.out;
}
ComponentLoadResult camshaft(Image& m) {
    if(m.count()!=9) return m.fail(1);
    const auto material=truncated(m.number(0x40));
    if(!(same_engine_family(m) && m.bounded(0x30,5.f,25.f) &&
        m.bounded(0x48,5.f,20.f) && m.bounded(0x4c,5.f,20.f) &&
        m.rounded_between(0x3c,0,2) && m.rounded_between(0x40,0,9) &&
        material!=8 && material!=9 && m.bounded(0x44,.9f,1.1f))) return m.fail(2);
    m.add_mass();m.copy(0x52c,0x30);m.copy(0x53c,0x44);m.copy(0x540,0x53b);
    m.integer(0x530,nearest(m.number(0x34)));m.integer(0x534,nearest(m.number(0x3c)));
    m.integer(0x538,nearest(m.number(0x40)));m.copy(0x544,0x48,24);
    material_quality(m,0x40);return m.out;
}
ComponentLoadResult valve_train(Image& m) {
    if(m.count()!=3) return m.fail(1);
    if(!(same_engine_family(m) && m.bounded(0x30,5.f,30.f) &&
        m.rounded_between(0x3c,0,2) && m.bounded(0x40,.9f,1.1f))) return m.fail(2);
    m.add_mass();m.copy(0x55c,0x30);m.copy(0x568,0x40);m.copy(0x56c,0x53b);
    m.integer(0x560,nearest(m.number(0x34)));m.integer(0x564,nearest(m.number(0x3c)));
    m.integer(0x570,truncated(m.number(0x44)));m.quality();return m.out;
}
ComponentLoadResult crankshaft(Image& m) {
    if(m.count()!=2) return m.fail(1);
    m.add_mass();m.copy(0x490,0x30);m.copy(0x49c,0x53b);m.copy(0x4a0,0x40);
    m.integer(0x494,nearest(m.number(0x34)));m.integer(0x498,nearest(m.number(0x3c)));
    const auto material=nearest(m.number(0x3c));
    if(!(same_engine_family(m) && m.bounded(0x30,15.f,50.f) &&
        m.rounded_between(0x34,0,3) && m.rounded_between(0x3c,0,9) &&
        material!=2 && material!=3 && material!=9)) {m.out.status=2;return m.out;}
    material_quality(m,0x3c);return m.out;
}
ComponentLoadResult connecting_rods(Image& m) {
    if(m.count()!=3) return m.fail(1);
    cylinder_mass(m,0x4a4,0x4ac);
    m.integer(0x4a8,nearest(m.number(0x34)));m.integer(0x4b0,nearest(m.number(0x3c)));
    m.copy(0x4b4,0x53b);m.copy(0x4b8,0x40);m.copy(0x4bc,0x44);
    const auto material=truncated(m.number(0x3c));
    if(!(same_engine_family(m) && m.bounded(0x30,.1f,2.f) &&
        m.rounded_between(0x34,0,3) && m.rounded_between(0x3c,0,9) &&
        material!=8 && material!=9 && m.bounded(0x40,30.f,250.f))) {m.out.status=2;return m.out;}
    material_quality(m,0x3c);return m.out;
}
ComponentLoadResult pistons(Image& m) {
    if(m.count()!=4) return m.fail(1);
    const auto material=truncated(m.number(0x40));
    if(!(same_engine_family(m) && m.bounded(0x30,.1f,2.f) &&
        m.rounded_between(0x3c,0,3) && m.rounded_between(0x40,0,9) &&
        m.bounded(0x44,-1.f,4.f) && material!=8 && material!=9)) return m.fail(2);
    cylinder_mass(m,0x470,0x478);
    m.integer(0x474,nearest(m.number(0x34)));m.integer(0x47c,nearest(m.number(0x3c)));
    m.integer(0x480,nearest(m.number(0x40)));
    m.copy(0x484,0x44);m.copy(0x488,0x53b);m.copy(0x48c,0x48);
    m.put(0x54,m.existing(0x54)+m.number(0x44));material_quality(m,0x40);return m.out;
}
ComponentLoadResult tire(Image& m,std::span<const std::byte> templates) {
    if(templates.empty()) return m.fail(4);
    if(templates.size()!=0x1d68) throw std::invalid_argument("expected tire auxiliary image");
    if(m.count()!=4) return m.fail(1);
    if(!(m.bounded(0x3c,100.f,500.f) && m.bounded(0x40,25.f,95.f) &&
        m.bounded(0x44,12.f,25.f) && m.bounded(0x30,8.f,30.f) &&
        m.rounded_between(0x34,0,3))) return m.fail(2);
    const auto index=truncated(m.number(0x48));
    if(index<0 || index>=20) throw std::invalid_argument("tire template index outside original allocation");
    const auto base=index*0x178;
    auto parameter=[&](std::size_t offset) {return finite(std::bit_cast<float>(word(templates,base+offset)));};
    m.add_mass(1.);
    const double width=m.number(0x3c);
    if(width>215.) {
        const auto increment=std::clamp(static_cast<float>((width-215.)*.00004f),0.f,.005f);
        m.put(0,m.existing(0)+increment);
    }
    const auto shift=m.front() ? 0 : 0x104;
    m.copy(0x220+shift,0x30);m.integer(0x224+shift,truncated(m.number(0x34)));
    for(auto p:std::array<std::array<std::size_t,2>,3>{{{0x124,0x3c},{0x128,0x40},{0x12c,0x44}}}) m.copy(p[0]+shift,p[1]);
    m.put(0x138+shift,0.);
    std::fill(m.out.configuration.begin()+0x150+shift,m.out.configuration.begin()+0x220+shift,std::byte{0});
    for(auto p:std::array<std::array<std::size_t,2>,6>{{{0x134,8},{0x130,12},
        {0x140,0x170},{0x13c,0x168},{0x144,0x178},{0x148,0x174}}}) m.put(p[0]+shift,parameter(p[1]));
    m.put(0x14c+shift,parameter(0x16c)*.01f);
    std::copy_n(templates.begin()+base+0xa0,100,m.out.configuration.begin()+0x154+shift);
    std::copy_n(templates.begin()+base+0x104,100,m.out.configuration.begin()+0x1bc+shift);
    m.quality_value(m.number(0x48)==4. ? .96f : 1.f);
    if(!(m.existing(0x140+shift)>=.7f && m.existing(0x140+shift)<=2. &&
        m.existing(0x144+shift)>=127. && m.existing(0x144+shift)<=508.)) m.out.status=2;
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
    std::span<const std::byte> config,std::span<const std::byte> component,
    std::span<const std::byte> tire_templates) {
    Image image(config,component);
    switch(kind) {
        case 160001:return engine(image);
        case 1000001:return cylinder_head(image);
        case 1100001:return camshaft(image);
        case 1200001:return valve_train(image);
        case 180001:return crankshaft(image);
        case 190001:return connecting_rods(image);
        case 200001:return pistons(image);
        case 110001:return tire(image,tire_templates);
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
