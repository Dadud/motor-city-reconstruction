#include "mco/drafting.hpp"
#include <algorithm>
#include <cmath>
#include <set>
#include <stdexcept>
#include <utility>

namespace mco {
namespace {
using Vector=std::array<double,3>;
double f(double value) {
    const double stored=static_cast<float>(value);
    if(!std::isfinite(stored)) throw std::invalid_argument("finite float32 value required");
    return stored;
}
template<class T> void normalize(T& values) { for(auto& value:values) value=f(value); }
double dot(const Vector& a,const Vector& b) { return (a[0]*b[0]+a[1]*b[1])+a[2]*b[2]; }
Vector cross(const Vector& a,const Vector& b) {
    return {f(a[1]*b[2]-a[2]*b[1]),f(a[2]*b[0]-a[0]*b[2]),f(a[0]*b[1]-a[1]*b[0])};
}
}
DraftingOutput calculate_drafting(std::int64_t identifier,std::vector<DraftVehicle> cars) {
    std::set<std::int64_t> identities;
    for(auto& car:cars) {
        if(car.identifier<0 || !identities.insert(car.identifier).second)
            throw std::invalid_argument("unique nonnegative vehicle identifiers required");
        normalize(car.position);normalize(car.basis);normalize(car.half_extents);normalize(car.wake_origin);
        for(auto& normal:car.wake_normals) normalize(normal);
        if(*std::min_element(car.half_extents.begin(),car.half_extents.end())<=0)
            throw std::invalid_argument("positive vehicle half extents required");
    }
    const auto found=std::find_if(cars.begin(),cars.end(),[identifier](const auto& c){return c.identifier==identifier;});
    if(found==cars.end()) throw std::invalid_argument("current vehicle identifier required");
    const DraftVehicle own=*found;
    const double length=own.half_extents[2],reach=f(length*6);
    const Vector forward{own.basis[6],own.basis[7],own.basis[8]};
    Vector sample{};
    for(unsigned i=0;i<3;i++) sample[i]=f(forward[i]*length+own.position[i]);
    for(auto& car:cars) {
        if(car.identifier==identifier) continue;
        const double dx=f(own.position[0]-car.position[0]);
        const double dz=f(own.position[2]-car.position[2]);
        const double distance=f(std::sqrt(dx*dx+dz*dz));
        if(distance>reach) continue;
        const double alignment=dot(forward,{car.basis[6],car.basis[7],car.basis[8]});
        if(alignment<f(.9659258)) continue;
        const double stored_alignment=f(alignment);
        Vector side{},up{},back{};
        for(unsigned i=0;i<3;i++) {
            side[i]=car.basis[i]*car.half_extents[0];
            up[i]=car.basis[3+i]*car.half_extents[1];
            back[i]=car.basis[6+i]*f(car.half_extents[2]*4);
        }
        side[0]=f(side[0]);side[1]=f(side[1]);
        up[1]=f(up[1]);up[2]=f(up[2]);
        back[1]=f(back[1]);back[2]=f(back[2]);
        constexpr std::array<int,4> sign_x{1,1,-1,-1},sign_y{1,-1,-1,1};
        std::array<Vector,4> corners{};
        for(unsigned n=0;n<4;n++) for(unsigned i=0;i<3;i++)
            corners[n][i]=f(sign_x[n]*side[i]+sign_y[n]*up[i]-back[i]);
        for(unsigned n=0;n<4;n++) car.wake_normals[n]=cross(corners[n],corners[(n+1)%4]);
        for(unsigned i=0;i<3;i++) car.wake_origin[i]=f(car.half_extents[2]*3*car.basis[6+i]+car.position[i]);
        Vector relative{};
        for(unsigned i=0;i<3;i++) relative[i]=f(sample[i]-car.wake_origin[i]);
        const bool inside=std::all_of(car.wake_normals.begin(),car.wake_normals.end(),
            [&relative](const auto& normal){return dot(relative,normal)>=0;});
        double factor;
        if(inside) factor=f(((f(1.0340742)-stored_alignment)*(distance+reach)*.25)/(reach*f(.034074187)));
        else factor=distance==0?1.25:std::clamp(f((length/distance)*.25+1),1.,1.25);
        const auto selected=car.identifier;
        return {factor,std::move(cars),selected,inside};
    }
    return {1.,std::move(cars),std::nullopt,false};
}
}
