"""Original altitude table and weather-dependent air-density calculation."""
import math
from client.tire_response import f32

_DENSITIES=tuple(map(f32,(1.347,1.2849,1.225,1.1673,1.1117,1.0581,1.0066,
                         .95695,.90925,.8634,.81935,.77704,.73643)))


def calculate_air_density(altitude: float, cold_environment: bool,
                          weather_enabled: bool, weather_code: int) -> float:
    if type(cold_environment) is not bool or type(weather_enabled) is not bool:
        raise ValueError('boolean environment flags required')
    if type(weather_code) is not int or not 0<=weather_code<=0xffffffff:
        raise ValueError('unsigned weather code required')
    shifted=f32(f32(altitude)+500)
    index=math.floor(shifted*f32(.002))
    if not 0<=index<12:
        raise ValueError('altitude outside verified original density table interval')
    temperature=f32(278.15 if cold_environment else 288.15)
    selected=weather_code if weather_enabled else 0
    if selected==2: temperature=f32(temperature-20)
    elif selected==1: temperature=f32(temperature-10)
    density=_DENSITIES[index]+(_DENSITIES[index+1]-_DENSITIES[index])*(shifted-index*500)*f32(.002)
    return f32(density*f32(288.15)/temperature)
