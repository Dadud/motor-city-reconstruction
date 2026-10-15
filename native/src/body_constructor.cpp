#include "mco/body_constructor.hpp"
#include "mco/owner_binding.hpp"
#include <algorithm>
#include <bit>
#include <cmath>
#include <stdexcept>

namespace mco {
namespace {
double rounded(double value) { return static_cast<float>(value); }
void validate_shape(BodyShape shape) {
    if(static_cast<unsigned>(shape)>4) throw std::invalid_argument("original body shape must be 0..4");
}
}

BodySamples body_samples(BodyShape shape, std::array<float,3> half_extents) {
    validate_shape(shape);
    for(auto v:half_extents) if(!std::isfinite(v) || std::abs(v)>1e6f)
        throw std::invalid_argument("finite bounded half extents required");
    const double x=half_extents[0], y=half_extents[1], z=half_extents[2];
    const double nx=-x, ny=-y, nz=-z;
    using Point=std::array<double,3>;
    std::array<Point,22> p{};
    p[0]={nx,ny,z};p[1]={x,ny,z};p[2]={x,ny,nz};p[3]={nx,ny,nz};
    if(shape==BodyShape::pyramid) {
        for(unsigned i=4;i<8;++i) p[i]={0.,y,0.};
    } else if(shape==BodyShape::wedge && x<=z) {
        p[4]={0.,y,z};p[5]={0.,y,z};p[6]={0.,y,nz};p[7]={0.,y,nz};
    } else if(shape==BodyShape::wedge) {
        p[4]={nx,y,0.};p[5]={x,y,0.};p[6]={x,y,0.};p[7]={nx,y,0.};
    } else {
        p[4]={nx,y,z};p[5]={x,y,z};p[6]={x,y,nz};p[7]={nx,y,nz};
    }
    const auto a=p[4],b=p[5],c=p[6],d=p[7];
    const auto rx=c[0]+d[0],ry=d[1]+c[1],rz=c[2]+d[2],bx=nx+x,by=ny+ny;
    // Preserve original addition order and storage points, including signed zeros.
    p[8]={(b[0]+a[0]+nx+x)*.25,(ny+ny+a[1]+b[1])*.25,(z+z+b[2]+a[2])*.25};
    p[9]={(rx+nx+x)*.25,(ny+ny+ry)*.25,(nz+nz+rz)*.25};
    p[10]={(nx+nx+d[0]+a[0])*.25,(ny+ny+d[1]+a[1])*.25,(nz+d[2]+a[2]+z)*.25};
    p[11]={(x+x+c[0]+b[0])*.25,(ny+ny+c[1]+b[1])*.25,(nz+c[2]+b[2]+z)*.25};
    p[12]={(rx+b[0]+a[0])*.25,(ry+a[1]+b[1])*.25,(rz+b[2]+a[2])*.25};
    p[13]={(nx+bx+x)*.25,(ny+ny+by)*.25,(z+z+nz+nz)*.25};
    p[14]={(b[0]+a[0])*.5,(a[1]+b[1])*.5,(b[2]+a[2])*.5};
    p[15]={(c[0]+b[0])*.5,(c[1]+b[1])*.5,(c[2]+b[2])*.5};
    p[16]={(d[0]+a[0])*.5,(d[1]+a[1])*.5,(d[2]+a[2])*.5};
    p[17]={rx*.5,ry*.5,rz*.5};
    p[18]={bx*.5,by*.5,(z+z)*.5};p[19]={(x+x)*.5,by*.5,(nz+z)*.5};
    p[20]={(nx+nx)*.5,by*.5,(nz+z)*.5};p[21]={bx*.5,by*.5,(nz+nz)*.5};
    BodySamples result{};
    for(unsigned i=0;i<22;++i) for(unsigned axis=0;axis<3;++axis) result[i][axis]=static_cast<float>(p[i][axis]);
    if(shape==BodyShape::cylinder || shape==BodyShape::sphere) {
        for(unsigned i=0;i<8;++i) for(unsigned axis=0;axis<3;++axis)
            if(shape==BodyShape::sphere || axis!=1) result[i][axis]=static_cast<float>(static_cast<double>(result[i][axis])*.707f);
        if(shape==BodyShape::sphere) for(unsigned i=14;i<22;++i)
            result[i][1]=static_cast<float>(static_cast<double>(result[i][1])*.707f);
    }
    return result;
}

BodySamples customize_body_samples(unsigned selector,const BodySamples& samples) {
    if(selector>7) throw std::invalid_argument("catalogue body selector must be 0..7");
    auto out=samples;
    for(const auto& point:out) for(auto value:point) if(!std::isfinite(value) || std::abs(value)>1e6f)
        throw std::invalid_argument("bounded finite samples required");
    auto scale=[&](std::initializer_list<unsigned> indices,float factor) {
        for(auto i:indices) out[i/3][i%3]=static_cast<float>(static_cast<double>(out[i/3][i%3])*factor);
    };
    switch(selector) {
    case 1:scale({22,19,52},.3f);scale({13,16,43},.5f);scale({2,5,56,14,17,44},.9f);break;
    case 2:case 4:
        if(selector==2) {scale({20,53,23},.8f);scale({29},.95f);}
        scale({17,14},.8f);scale({44},.9f);scale({22,19},.3f);scale({52,43},.4f);scale({13,16},.3f);break;
    case 5:scale({22,19,52},.3f);scale({13,16,43},.4f);break;
    case 6:
        scale({3,0,46,45,48,49,15,12,18,21,11,8},.8f);scale({17,14,44},.85f);
        scale({9,6,65},.9f);scale({22,19,52},.7f);scale({13,16},.3f);scale({43},.4f);break;
    case 7:scale({13,16,43},.3f);break;
    }
    return out;
}

StartupOwnerImage construct_body(std::span<const std::byte> owner,std::uint32_t identity,
        float input_mass,std::array<float,3> dimensions,BodyShape shape,std::uint32_t material) {
    validate_shape(shape);
    if(owner.size()!=0x2000) throw std::invalid_argument("expected full startup observation image");
    if(!std::isfinite(input_mass) || input_mass<0 || input_mass>1e6f)
        throw std::invalid_argument("bounded nonnegative mass required");
    for(auto v:dimensions) if(!std::isfinite(v) || v<1e-3f || v>1e3f)
        throw std::invalid_argument("bounded positive half extents required");
    if(shape==BodyShape::sphere) dimensions.fill(*std::max_element(dimensions.begin(),dimensions.end()));
    const double x=dimensions[0],y=dimensions[1],z=dimensions[2],mass=input_mass==0?1000.:input_mass;
    StartupOwnerImage out;std::copy(owner.begin(),owner.end(),out.begin());std::fill_n(out.begin(),0x418,std::byte{0});
    auto word=[&](std::size_t offset,std::uint32_t value) {
        for(unsigned k=0;k<4;++k) out[offset+k]=static_cast<std::byte>((value>>(k*8))&255);
    };
    auto put=[&](std::size_t offset,double value){word(offset,std::bit_cast<std::uint32_t>(static_cast<float>(value)));};
    word(0,identity);word(0x58,material);word(0xdc,static_cast<unsigned>(shape));
    put(0xcc,x);put(0xd0,y);put(0xd4,z);put(0xd8,std::sqrt(z*z+y*y+x*x));
    word(0x30,0xc11cf5c3);put(0x50,mass);put(0x54,1./mass);
    const double sx=rounded(x*x*4.),sy=rounded(y*y*4.),sz=rounded(z*z*4.);
    const double dx=rounded(x+x),dy=rounded(y+y),dz=rounded(z+z);
    const double box=1.f/12.f,taper=.0125f;
    std::array<double,3> inertia{};std::array<double,4> response{.31f,1.,1.,1.};double volume=0;
    switch(shape) {
    case BodyShape::box:
        inertia={(sz+sy)*mass*box,(sz+sx)*mass*box,(sy+sx)*mass*box};volume=dz*dy*dx;break;
    case BodyShape::pyramid:
        response={.31f,.5,1.,.5};
        inertia={(sz*4.+sy*8.)*mass*taper,(sz+sx)*mass*.05f,(sx*4.+sy*8.)*mass*taper};volume=dz*dx*dy*.25;break;
    case BodyShape::wedge:
        if(x<=z) {response={.31f,.5,1.,1.};inertia={(sy*8.+sz*4.)*mass*taper,(sz+sx)*mass*box,(sy+sx)*mass*box};}
        else {response={.31f,1.,1.,.5};inertia={(sz+sy)*mass*box,(sz+sx)*mass*box,(sx*4.+sy*8.)*mass*taper};}
        volume=dz*dx*dy*.5;break;
    case BodyShape::cylinder: {
        response[2]=std::bit_cast<float>(0x3f34fdf4u);const auto radius=rounded(std::sqrt(x*x+z*z));
        inertia={(sz+sy)*mass*box,radius*radius*mass*.5,(sy+sx)*mass*box};volume=radius*radius*dy*3.1415927410125732f;break;
    }
    case BodyShape::sphere:
        response={.31f,std::bit_cast<float>(0x3f34fdf4u),std::bit_cast<float>(0x3f34fdf4u),std::bit_cast<float>(0x3f34fdf4u)};
        inertia.fill(x*mass*.4f);volume=rounded(x*x)*x*4.188790321350098f;break;
    }
    volume=rounded(volume);put(0x74,volume);put(0x70,mass/volume);
    for(unsigned axis=0;axis<3;++axis) {put(0x2f0+axis*4,inertia[axis]);put(0x2fc+axis*4,1./rounded(inertia[axis]));}
    for(unsigned axis=0;axis<4;++axis) put(0x308+axis*4,response[axis]);
    const auto points=body_samples(shape,dimensions);
    for(unsigned i=0;i<22;++i) for(unsigned axis=0;axis<3;++axis) {
        put(0xe0+i*12+axis*4,points[i][axis]);put(0x1e8+i*12+axis*4,points[i][axis]);
    }
    put(0x408,.875);word(0x40c,0x3eaaa64c);
    double restitution=.1f,friction=.45f;
    switch(material) {
    case 1:restitution=.15f;friction=.35f;break;
    case 2:restitution=.2f;friction=.5f;break;
    case 3:restitution=.05f;friction=.1f;break;
    case 4:restitution=.35f;friction=1.;break;
    case 5:restitution=.05f;friction=.7f;break;
    case 6:restitution=.25f;friction=.5f;put(0x308,.37f);break;
    }
    put(0x68,restitution);put(0x318,friction);
    for(auto offset:{0x78,0x9c}) for(unsigned i=0;i<9;++i) put(offset+i*4,i%4==0?1.:0.);
    put(0xc4,1.);word(0x400,1);word(0x404,1);out[4]=std::byte{1};
    return out;
}

StartupOwnerImage prepare_startup_body(std::span<const std::byte> owner,std::span<const std::byte> config,
        std::array<float,3> extents,std::uint32_t identity,bool finalized) {
    if(!finalized || config.size()!=0x820) throw std::invalid_argument("finalized mechanical configuration required");
    auto word=[&](std::span<const std::byte> image,unsigned offset) {
        std::uint32_t result=0;for(unsigned k=0;k<4;++k) result|=std::to_integer<std::uint32_t>(image[offset+k])<<(k*8);return result;
    };
    auto number=[&](std::span<const std::byte> image,unsigned offset){return std::bit_cast<float>(word(image,offset));};
    auto out=construct_body(owner,identity,number(config,0x20),extents,BodyShape::box,0);
    auto put=[&](unsigned offset,std::uint32_t value) {for(unsigned k=0;k<4;++k) out[offset+k]=static_cast<std::byte>((value>>(k*8))&255);};
    const auto selector=word(config,0x48);
    auto samples=customize_body_samples(selector,body_samples(BodyShape::box,extents));
    out[6]=std::byte{1};put(0x318,0x3f266666);
    for(unsigned i=0;i<22;++i) for(unsigned axis=0;axis<3;++axis) put(0xe0+i*12+axis*4,std::bit_cast<std::uint32_t>(samples[i][axis]));
    out=adjust_owner_stance(out);
    put(0x30c,selector==0 || selector==6 || selector==7?0x3f666666:0x3f4ccccd);
    put(0x310,0x3f800000);put(0x314,selector==0 || selector==1 || selector==7?0x3f733333:0x3f4ccccd);
    put(0x308,word(config,0));
    const auto com=bind_startup_com(number(config,0x38),number(out,0xd0),number(out,0x18c4),number(out,0x18b8));
    put(0x60,std::bit_cast<std::uint32_t>(com.vertical));put(0x64,std::bit_cast<std::uint32_t>(com.longitudinal));
    return out;
}
}
