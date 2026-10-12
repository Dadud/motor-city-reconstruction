"""EA SHPI image and RefPack/QFS decoding with bounded reads.

Format reference: LibOpenNFS Shared/FSH (MIT); implementation authored here.
Only image formats explicitly handled below are admitted. First mip level only.
"""
from dataclasses import dataclass
import struct


def unpack_qfs(data: bytes, max_bytes=64*1024*1024) -> bytes:
    if len(data) < 5 or data[0] not in (0x10, 0x11) or data[1] != 0xfb:
        raise ValueError('unsupported QFS header')
    expected = int.from_bytes(data[2:5], 'big')
    if expected > max_bytes:
        raise ValueError('QFS output exceeds budget')
    cursor = 8 if data[0] & 1 else 5
    out = bytearray()

    def take(count):
        nonlocal cursor
        if cursor+count > len(data):
            raise ValueError('truncated QFS command')
        value = data[cursor:cursor+count]
        cursor += count
        return value

    def literals(count):
        if len(out)+count > expected:
            raise ValueError('QFS literals exceed declared output')
        out.extend(take(count))

    while True:
        command = take(1)[0]
        if command >= 0xfc:
            literals(command & 3)
            break
        if command >= 0xe0:
            literals(((command & 31)+1)*4)
            continue
        if command < 0x80:
            b = take(1)[0]
            literal, length, distance = command & 3, ((command >> 2) & 7)+3, ((command >> 5)<<8)+b+1
        elif command < 0xc0:
            b, c = take(2)
            literal, length, distance = b >> 6, (command & 63)+4, ((b & 63)<<8)+c+1
        else:
            b, c, d = take(3)
            literal, length, distance = command & 3, ((command & 12)<<6)+d+5, ((command & 16)<<12)+(b<<8)+c+1
        literals(literal)
        if distance > len(out) or len(out)+length > expected:
            raise ValueError('invalid QFS backreference')
        start = len(out)-distance
        pattern = bytes(out[start:start+min(distance,length)])
        out.extend((pattern*((length+len(pattern)-1)//len(pattern)))[:length])
    if len(out) != expected:
        raise ValueError('QFS output size mismatch')
    return bytes(out)


@dataclass(frozen=True)
class Texture:
    name: str
    width: int
    height: int
    rgba: bytes


def _rgba16(value, kind):
    if kind == 0x7e:
        return ((value>>10 & 31)*255//31, (value>>5 & 31)*255//31, (value & 31)*255//31,
                255 if value & 0x8000 else 0)
    if kind == 0x78:
        return ((value>>11)*255//31, (value>>5 & 63)*255//63, (value & 31)*255//31, 255)
    return ((value>>8 & 15)*17, (value>>4 & 15)*17, (value & 15)*17, (value>>12)*17)


def _decode_pixels(raw, width, height, kind):
    count = width*height
    sizes = {0x7d:4, 0x7f:3, 0x7e:2, 0x78:2, 0x6d:2}
    if kind in (0x60,0x61):
        stride = 8 if kind == 0x60 else 16
        required = ((width+3)//4)*((height+3)//4)*stride
        if len(raw) < required:
            raise ValueError('truncated DXT image')
        pixels = bytearray(count*4)
        cursor = 0
        for by in range(0,height,4):
            for bx in range(0,width,4):
                alpha = int.from_bytes(raw[cursor:cursor+8],'little') if kind == 0x61 else None
                colour_start = cursor+(8 if kind==0x61 else 0)
                c0,c1,bits = struct.unpack_from('<HHI',raw,colour_start)
                a,b = _rgba16(c0,0x78),_rgba16(c1,0x78)
                colours = [a,b]
                if c0>c1 or kind==0x61:
                    colours += [tuple((2*a[i]+b[i])//3 for i in range(3))+(255,),
                                tuple((a[i]+2*b[i])//3 for i in range(3))+(255,)]
                else:
                    colours += [tuple((a[i]+b[i])//2 for i in range(3))+(255,), (0,0,0,0)]
                for y in range(4):
                    for x in range(4):
                        k=y*4+x
                        colour = colours[(bits>>(k*2)) & 3]
                        if alpha is not None:
                            colour = colour[:3]+(((alpha>>(k*4)) & 15)*17,)
                        if bx+x<width and by+y<height:
                            offset=((by+y)*width+bx+x)*4
                            pixels[offset:offset+4]=bytes(colour)
                cursor += stride
        return bytes(pixels)
    if kind not in sizes:
        raise ValueError(f'unsupported FSH pixel type 0x{kind:02x}')
    stride = sizes[kind]
    if len(raw)<count*stride:
        raise ValueError('truncated image pixels')
    rgba=bytearray(count*4)
    for p in range(count):
        if stride==2:
            colour=_rgba16(struct.unpack_from('<H',raw,p*2)[0],kind)
        else:
            b,g,r=raw[p*stride:p*stride+3]
            colour=(r,g,b,raw[p*stride+3] if stride==4 else 255)
        rgba[p*4:p*4+4]=bytes(colour)
    return bytes(rgba)


def decode_fsh(data: bytes, max_pixels=16_777_216) -> tuple[Texture,...]:
    if data[:2] in (b'\x10\xfb',b'\x11\xfb'):
        data=unpack_qfs(data)
    if len(data)<16 or data[:4]!=b'SHPI':
        raise ValueError('unsupported FSH container')
    size,count=struct.unpack_from('<II',data,4)
    if size!=len(data) or 16+count*8>size:
        raise ValueError('invalid FSH directory size')
    descriptors=[]
    for index in range(count):
        name,offset=struct.unpack_from('<4sI',data,16+index*8)
        if offset<16+count*8 or offset+16>size:
            raise ValueError('FSH entry outside file')
        descriptors.append((name,offset))
    offsets=sorted(set(offset for _,offset in descriptors))
    images=[]
    total_pixels=0
    for name,offset in descriptors:
        boundary=next((value for value in offsets if value>offset),size)
        code,width,height=struct.unpack_from('<IHH',data,offset)
        kind=code & 0x7f
        if kind in (0x22,0x24,0x29,0x2a,0x2d,0x6f):
            continue
        total_pixels+=width*height
        if not width or not height or total_pixels>max_pixels:
            raise ValueError('invalid FSH dimensions or pixel budget')
        link=code>>8
        if link:
            if link<16 or offset+link>boundary:
                raise ValueError('FSH attachment link outside entry')
            boundary=offset+link
        raw=data[offset+16:boundary]
        if code & 0x80:
            raw=unpack_qfs(raw)
        if kind==0x7b:
            palette_offset=offset+link if link else next((p for n,p in descriptors if n.lower()==b'!pal'),0)
            if not palette_offset or palette_offset+16>size or len(raw)<width*height:
                raise ValueError('indexed FSH missing palette or pixels')
            palette_code,entries=struct.unpack_from('<IH',data,palette_offset)
            palette_kind=palette_code & 0x7f
            palette_size={0x24:3,0x22:3,0x2a:4,0x29:2,0x2d:2}.get(palette_kind)
            if not palette_size or not 1<=entries<=256 or palette_offset+16+entries*palette_size>size:
                raise ValueError('invalid FSH palette')
            palette_data=data[palette_offset+16:palette_offset+16+entries*palette_size]
            if palette_kind==0x22:
                palette_data=bytes(min(255,x*4) for x in palette_data)
            pixel_kind={0x24:0x7f,0x22:0x7f,0x2a:0x7d,0x29:0x78,0x2d:0x7e}[palette_kind]
            palette=_decode_pixels(palette_data,entries,1,pixel_kind)
            if any(index>=entries for index in raw[:width*height]):
                raise ValueError('FSH index exceeds palette')
            rgba=b''.join(palette[index*4:index*4+4] for index in raw[:width*height])
        else:
            rgba=_decode_pixels(raw,width,height,kind)
        images.append(Texture(name.decode('latin-1'),width,height,rgba))
    return tuple(images)
