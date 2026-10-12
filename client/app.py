"""The growing portable client: browse local vehicle geometry in a modern window."""
import argparse
import json
import math
import platform
from pathlib import Path
import sys
from dataclasses import asdict
from .assets import Assets
from . import settings
from .assembly import PROFILES, select_body, stock_body_flags
from .scene import stock_scene
from .track import decode_track
from .track_mesh import decode_mesh
from .textures import decode_fsh

VERTEX_SHADER = '''#version 330 core
in vec3 position;
in vec3 normal;
in vec2 uv;
uniform mat4 mvp;
uniform mat4 object_to_world;
out float light;
out vec2 texcoord;
void main() {
    gl_Position = mvp * vec4(position, 1.0);
    float len = length(normal);
    vec3 n = len > 0.0001 ? mat3(object_to_world) * normal / len : vec3(0, 1, 0);
    light = 0.3 + 0.7 * abs(dot(n, normalize(vec3(0.4, 0.8, 0.6))));
    texcoord = vec2(uv.x, 1.0 - uv.y);
}
'''
FRAGMENT_SHADER = '''#version 330 core
in float light;
in vec2 texcoord;
uniform vec4 paint;
uniform sampler2D surface;
uniform bool textured;
out vec4 fragment;
void main() {
    vec4 colour = textured ? texture(surface, texcoord) : paint;
    if (colour.a < 0.02) discard;
    fragment = vec4(colour.rgb * light, colour.a);
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, help='installed game folder')
    parser.add_argument('--model', help='model archive, e.g. 32ford.viv')
    parser.add_argument('--track', help='track folder, e.g. Boothill; combine with --vehicle for world view')
    parser.add_argument('--track-mesh', action='store_true', help='render decoded base geometry instead of road corridor')
    parser.add_argument('--track-textures', action='store_true', help='apply original track UVs and day texture pages')
    parser.add_argument('--track-view', choices=('overview','start'), default='overview', help='initial track camera')
    parser.add_argument('--vehicle', type=int, help='stock branded vehicle ID, e.g. 101')
    parser.add_argument('--list-vehicles', action='store_true', help='list stock vehicle identities and exit')
    parser.add_argument('--stock-parts', action='store_true', help='print --vehicle stock component recipe and exit')
    parser.add_argument('--contact-report', action='store_true', help='report stock wheel contacts and spawn pose for --vehicle and --track')
    parser.add_argument('--skin', help='explicit FSH filename in Data/Skins')
    parser.add_argument('--body-style', choices=('stock', *PROFILES), help='stock selection or body configuration preview')
    parser.add_argument('--screenshot', type=Path, help='render once to PNG, then exit')
    parser.add_argument('--verify-controls', action='store_true', help='exercise controls before screenshot')
    parser.add_argument('--drive', action='store_true', help='offline driving with authored prototype physics; requires --vehicle and --track')
    parser.add_argument('--verify-driving', action='store_true', help='exercise driving, braking and reset before screenshot')
    parser.add_argument('--verify-race', action='store_true', help='complete a Drag sprint through input/update/render before screenshot')
    args = parser.parse_args()
    if args.track_mesh and not args.track:
        parser.error('--track-mesh requires --track')
    if args.track_textures and not args.track_mesh:
        parser.error('--track-textures requires --track-mesh')
    if args.contact_report and (args.vehicle is None or not args.track):
        parser.error('--contact-report requires --vehicle and --track')
    if args.contact_report and any((args.model,args.skin,args.body_style,args.stock_parts,args.list_vehicles,args.screenshot)):
        parser.error('--contact-report cannot be combined with other vehicle or capture modes')
    world_view = bool(args.track and args.vehicle is not None and not args.contact_report)
    if args.drive and not world_view:
        parser.error('--drive requires --vehicle and --track')
    if args.verify_driving and not (args.drive and args.screenshot):
        parser.error('--verify-driving requires --drive and --screenshot')
    if args.verify_race and not (args.drive and args.screenshot and args.track.casefold() == 'drag'):
        parser.error('--verify-race requires --drive, --track Drag and --screenshot')
    if args.track and not args.contact_report and (args.model or
            (not world_view and (args.skin or args.body_style))):
        parser.error('track world view requires --vehicle; --model is a garage option')
    if world_view:
        if args.body_style not in (None, 'stock'):
            parser.error('world view currently uses the stock vehicle assembly')
        args.track_mesh = args.track_textures = True
    if args.verify_controls and not args.screenshot:
        parser.error('--verify-controls requires --screenshot')
    if args.vehicle is not None and args.model:
        parser.error('choose either --vehicle or --model')
    if args.stock_parts and args.vehicle is None:
        parser.error('--stock-parts requires --vehicle')
    if args.body_style == 'stock' and args.vehicle is None:
        parser.error('--body-style stock requires --vehicle')
    previous = settings.load()
    chosen_model = args.model or previous.get('model', '32ford.viv')
    root = args.data or previous.get('data_root')
    if not root:
        parser.error('use --data /path/to/MotorCityOnline for the first launch')
    try:
        assets = Assets(root)
        selected_vehicle = None
        if args.vehicle is not None or args.list_vehicles:
            from .catalogue import Catalogue
            database = assets.paths.get('data/db/online.mdb')
            if database is None:
                raise ValueError('missing Data/DB/Online.mdb')
            catalogue = Catalogue.load(database)
            if args.list_vehicles:
                for identifier in sorted(catalogue.vehicles):
                    vehicle = catalogue.vehicle(identifier)
                    print(f'{identifier}\t{vehicle.year}\t{vehicle.name}')
                return
            selected_vehicle = catalogue.vehicle(args.vehicle)
            chosen_model = selected_vehicle.body_filename + '.viv'
            if args.stock_parts:
                print(json.dumps(asdict(selected_vehicle), indent=2))
                return
        if args.contact_report:
            from .contact import Pose, WheelRig
            from .track_surface import decode_surface
            path=assets.paths.get(f'data/tracks/{args.track}/tr.frd'.casefold())
            body=assets.paths.get(f'data/models/{chosen_model}'.casefold())
            if path is None or body is None:
                raise ValueError('contact report requires installed track and body assets')
            data=path.read_bytes()
            road=decode_track(data).slices[0]
            terrain=decode_surface(data)
            rig=WheelRig.from_model(assets.load_vehicle(body))
            dimensions=catalogue.tire_dimensions(selected_vehicle)
            suspension=catalogue.suspension(selected_vehicle)
            radii={key:tire.radius for key,tire in dimensions.items()}
            pose=Pose.yaw(road.position,math.atan2(road.forward[0],road.forward[2]))
            placed,contacts=rig.spawn_pose(terrain,pose,radii)
            camshaft=catalogue.camshaft(selected_vehicle)
            valve_train=catalogue.valve_train(selected_vehicle)
            print(json.dumps(dict(vehicle=selected_vehicle.branded_id,track=args.track,
                spawn_pose=asdict(placed),tire_dimensions={k:asdict(v) for k,v in dimensions.items()},
                suspension={k:dict(spring=asdict(v[0]),shock=asdict(v[1])) for k,v in suspension.items()},
                engine_block=asdict(catalogue.engine_block(selected_vehicle)),
                cylinder_head=asdict(catalogue.cylinder_head(selected_vehicle)),
                camshaft=asdict(camshaft),valve_train=asdict(valve_train),
                engine_family=catalogue.engine_family(selected_vehicle),
                flow_template_id=catalogue.engine_flow_template_id(selected_vehicle),
                effective_valve_lift_inches=camshaft.valve_lift_inches(valve_train.lift_factor),
                contacts=[asdict(c) for c in contacts]),indent=2))
            return
        paths = assets.vehicles()
        if args.track:
            paths = sorted(p for k,p in assets.paths.items() if k.startswith('data/tracks/') and
                           p.name.casefold() == 'tr.frd')
            chosen_model = args.track
            if not any(p.parent.name.casefold() == args.track.casefold() for p in paths):
                raise ValueError(f'track folder not found: {args.track}')
        if not paths:
            raise ValueError('no model archives found in Data/Models')
        if selected_vehicle and not args.track and not any(p.name.casefold() == chosen_model.casefold() for p in paths):
            raise ValueError(f'stock body archive missing: {chosen_model}')
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')
    # Import graphics only after data validation, so missing data reports clearly.
    import pyglet
    from pyglet import gl
    from pyglet.graphics.shader import Shader, ShaderProgram
    from pyglet.math import Mat4, Vec3
    from pyglet.window import key, mouse

    class Garage(pyglet.window.Window):
        def __init__(self):
            super().__init__(width=1280, height=800, caption='Motor City | Track corridor' if args.track else 'Motor City | Garage',
                             resizable=True, vsync=True, visible=not args.screenshot,
                             config=gl.Config(double_buffer=True, depth_size=24,
                                              major_version=3, minor_version=3))
            self.program = ShaderProgram(Shader(VERTEX_SHADER, 'vertex'), Shader(FRAGMENT_SHADER, 'fragment'))
            self.gate_mesh = self.program.vertex_list(6, gl.GL_LINES,
                position=('f', [0]*18), normal=('f', [0]*18), uv=('f', [0]*12)) if args.drive else None
            self.meshes = []
            self.gpu_textures = []
            self.vehicle_meshes = []
            self.vehicle_textures = []
            self.world_vehicle = None
            self.drive = None
            self.paused = False
            self.follow_car = True
            self.keys = key.KeyStateHandler()
            self.push_handlers(self.keys)
            self.texture_warning = ''
            self.body_style = args.body_style or ('stock' if selected_vehicle else None)
            self.body_flags = None
            self.assembly_notes = ()
            self.yaw, self.pitch, self.distance = 0.65, 0.3, 6.5
            self.part_index = None
            self.wireframe = False
            self.index = next((i for i, p in enumerate(paths) if
                (p.parent.name if args.track else p.name).casefold() == chosen_model.casefold()), 0)
            self.labels = [pyglet.text.Label(text, font_name='Arial', font_size=size,
                            color=color, x=x, y=y) for text, size, color, x, y in [
                ('MOTOR CITY', 13, (230, 187, 104, 255), 32, 760),
                ('Garage', 27, (235, 239, 242, 255), 32, 717),
                ('', 16, (224, 226, 231, 255), 32, 675),
                ('', 11, (153, 166, 181, 255), 32, 642),
                ('', 11, (187, 193, 204, 255), 32, 61),
                ('Drag: orbit   Scroll: zoom   Left / Right: model   Tab: isolate   [ / ]: part   W: wireframe   V: body style',
                 10, (153, 166, 181, 255), 32, 30)]]
            self.hud_panels = []
            if world_view:
                self.hud_panels = [pyglet.shapes.Rectangle(16, self.height-176, 410, 160,
                    color=(12, 17, 23, 220)), pyglet.shapes.Rectangle(16, 16, self.width-32, 65,
                    color=(12, 17, 23, 220))]
            self.error = ''
            if args.track:
                self.labels[5].text = 'Drag: orbit   Scroll: zoom   Left / Right: track   W: wireframe   Home: start   End: overview'
            if world_view:
                self.set_caption('Motor City | World')
                self.labels[5].text = 'Drag: orbit   Scroll: zoom   Left / Right: track   W: wireframe   Home: car   End: overview'
            if args.drive:
                self.set_caption('Motor City | Offline driving')
                self.labels[5].text = 'Arrows: drive / brake / steer   Shift + Up: reverse   R: reset   P: pause   PgUp / PgDn: track   Home / End: camera'
            self.load_model()
            if args.drive and not args.screenshot:
                pyglet.clock.schedule_interval(self.update_driving, 1/60)
            if args.screenshot:
                pyglet.clock.schedule_once(self.capture, 0.5)

        def load_model(self):
            for mesh, _ in self.vehicle_meshes:
                mesh.delete()
            for texture in self.vehicle_textures:
                if texture is not None:
                    texture.delete()
            self.vehicle_meshes, self.vehicle_textures = [], []
            self.world_vehicle = None
            self.drive = None
            for mesh,_ in self.meshes:
                mesh.delete()
            self.meshes = []
            for texture in self.gpu_textures:
                if texture is not None:
                    texture.delete()
            self.gpu_textures = []
            self.texture_warning = ''
            self.labels[2].text = (paths[self.index].parent.name if args.track else selected_vehicle.name if selected_vehicle and
                paths[self.index].name.casefold() == chosen_model.casefold() else paths[self.index].stem)
            self.labels[3].text = f'{self.index+1} / {len(paths)} models'
            try:
                prepared_textures = None
                self.assembly_notes = ()
                if args.track:
                    track_bytes = paths[self.index].read_bytes()
                    self.track_data = decode_track(track_bytes)
                    model = decode_mesh(track_bytes,materials=args.track_textures)[0] if args.track_mesh else self.track_data.corridor()
                    prepared_textures = ()
                    if args.track_textures:
                        name=paths[self.index].parent.name
                        texture_path=assets.paths.get(f'data/tracks/{name}/tr0.fsh'.casefold())
                        if texture_path is None:
                            raise ValueError(f'missing day track textures: {name}/TR0.fsh')
                        prepared_textures=decode_fsh(texture_path.read_bytes())
                    if world_view:
                        from .world import load_world_vehicle
                        self.world_vehicle = load_world_vehicle(assets, catalogue,
                            selected_vehicle, track_bytes, args.skin)
                        if args.drive:
                            from .driving import Drive
                            from .racing import TimeTrial
                            self.drive = Drive(self.world_vehicle, TimeTrial(self.track_data))
                        self.vehicle_textures = self.upload_textures(self.world_vehicle.textures)
                        self.vehicle_meshes = self.upload_meshes(self.world_vehicle.model)
                else:
                    model = assets.load_vehicle(paths[self.index])
                self.body_flags = None
                if self.body_style == 'stock':
                    if paths[self.index].name.casefold() == chosen_model.casefold():
                        model, prepared_textures, self.body_flags, self.assembly_notes = stock_scene(
                            assets, paths[self.index], selected_vehicle, args.skin)
                elif self.body_style:
                    model = select_body(model, PROFILES[self.body_style])
            except (OSError, KeyError, ValueError) as error:
                self.error = f'Could not load {paths[self.index].name}: {error}'
                self.labels[4].text = self.error
                return
            self.model = model
            self.error = ''
            try:
                textures = prepared_textures if prepared_textures is not None else assets.load_textures(paths[self.index], args.skin)
                for texture in textures:
                    if texture is None:
                        self.gpu_textures.append(None)
                        continue
                    image=pyglet.image.ImageData(texture.width,texture.height,'RGBA',texture.rgba,
                                                pitch=-texture.width*4)
                    gpu=image.get_texture()
                    gl.glBindTexture(gpu.target,gpu.id)
                    gl.glTexParameteri(gpu.target,gl.GL_TEXTURE_MIN_FILTER,gl.GL_LINEAR_MIPMAP_LINEAR)
                    gl.glTexParameteri(gpu.target,gl.GL_TEXTURE_MAG_FILTER,gl.GL_LINEAR)
                    gl.glGenerateMipmap(gpu.target)
                    self.gpu_textures.append(gpu)
            except ValueError as error:
                self.texture_warning=str(error)
            self.part_index = None
            vertices = [tuple(p.vertices[v][i] + p.origin[i] for i in range(3))
                        for p in model.parts for face in p.triangles for v in face.indices]
            if not vertices:
                self.error = 'This model has no renderable geometry.'
                self.labels[4].text = self.error
                return
            low = [min(v[i] for v in vertices) for i in range(3)]
            high = [max(v[i] for v in vertices) for i in range(3)]
            self.center = Vec3(*(0.5 * (a+b) for a, b in zip(low, high)))
            self.radius = max(max(b-a for a, b in zip(low, high)) * 0.5, 0.01)
            self.overview_center, self.overview_radius = self.center, self.radius
            if args.track and (args.track_view == 'start' or world_view):
                self.focus_start()
            self.rebuild()

        def upload_textures(self, textures):
            uploaded = []
            for texture in textures:
                if texture is None:
                    uploaded.append(None)
                    continue
                image = pyglet.image.ImageData(texture.width, texture.height, 'RGBA',
                    texture.rgba, pitch=-texture.width*4)
                gpu = image.get_texture()
                gl.glBindTexture(gpu.target, gpu.id)
                gl.glTexParameteri(gpu.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR_MIPMAP_LINEAR)
                gl.glTexParameteri(gpu.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
                gl.glGenerateMipmap(gpu.target)
                uploaded.append(gpu)
            return uploaded

        def upload_meshes(self, model):
            meshes = []
            for part in model.parts:
                for page in sorted({face.texture_page for face in part.triangles}):
                    positions, normals, coordinates = [], [], []
                    for face in part.triangles:
                        if face.texture_page != page:
                            continue
                        for corner, v in enumerate(face.indices):
                            positions.extend(part.vertices[v][i] + part.origin[i] for i in range(3))
                            normals.extend(part.normals[v])
                            coordinates.extend((face.uv[corner], face.uv[corner+3]))
                    meshes.append((self.program.vertex_list(len(positions)//3, gl.GL_TRIANGLES,
                        position=('f', positions), normal=('f', normals), uv=('f', coordinates)), page))
            return meshes

        def focus_start(self):
            road=self.track_data.slices[0]
            self.center=Vec3(*(self.drive.pose.position if self.drive else self.world_vehicle.pose.position if self.world_vehicle else road.position))
            self.radius=3 if self.world_vehicle else 10
            self.distance=3.5 if self.world_vehicle else 6.5
            self.pitch=0.2
            self.yaw=math.atan2(-road.forward[0],-road.forward[2])
            self.follow_car = True

        def update_driving(self, dt):
            if not self.drive or self.paused:
                return
            from .driving import Controls
            controls = Controls(float(bool(self.keys[key.UP])), float(bool(self.keys[key.DOWN] or self.keys[key.SPACE])),
                float(bool(self.keys[key.RIGHT]))-float(bool(self.keys[key.LEFT])),
                bool(self.keys[key.LSHIFT] or self.keys[key.RSHIFT]))
            self.drive.update(dt, controls)
            if self.follow_car:
                self.center = Vec3(*self.drive.pose.position)
            state = 'Terrain edge — steer or reset' if self.drive.blocked else 'Offline driving · Prototype physics'
            self.labels[4].text = f'{abs(self.drive.speed)*3.6:.0f} km/h   ·   {self.drive.distance:.0f} m   ·   {state}'
            self.labels[3].text = self.drive.trial.label()
            gate = self.drive.trial.gates[self.drive.trial.next_gate]
            if not self.drive.trial.finished:
                self.labels[3].text += f' · Next {math.dist(self.drive.pose.position, gate.position):.0f} m'

        def on_deactivate(self):
            if hasattr(self, 'keys'):
                self.keys.on_deactivate()
            if args.drive and hasattr(self, 'labels'):
                self.paused = True
                self.labels[4].text = 'Paused · P to resume'

        def rebuild(self):
            for mesh,_ in self.meshes:
                mesh.delete()
            self.meshes = []
            for index, part in enumerate(self.model.parts):
                if self.part_index is not None and index != self.part_index:
                    continue
                if not part.triangles:
                    continue
                pages=sorted(set(face.texture_page for face in part.triangles))
                for page in pages:
                    positions, normals, coordinates = [], [], []
                    for face in part.triangles:
                        if face.texture_page != page:
                            continue
                        for corner,v in enumerate(face.indices):
                            positions.extend(part.vertices[v][i] + part.origin[i] for i in range(3))
                            normals.extend(part.normals[v])
                            coordinates.extend((face.uv[corner],face.uv[corner+3]))
                    self.meshes.append((self.program.vertex_list(len(positions)//3, gl.GL_TRIANGLES,
                        position=('f', positions), normal=('f', normals), uv=('f',coordinates)), page))
            self.labels[2].text = (paths[self.index].parent.name if args.track else selected_vehicle.name if selected_vehicle and
                paths[self.index].name.casefold() == chosen_model.casefold() else paths[self.index].stem)
            self.labels[3].text = f'{self.index+1} / {len(paths)} models   ·   {self.model.triangle_count:,} triangles'
            if args.track:
                self.labels[1].text = 'Track geometry' if args.track_mesh else 'Track corridor'
                self.labels[3].text = f'{self.index+1} / {len(paths)} tracks   ·   {len(self.track_data.slices):,} road slices'
            self.labels[4].text = (('Body parts' if self.body_flags is not None or
                self.body_style in PROFILES else 'All parts') if self.part_index is None else
                                  f'Part {self.part_index+1}: {self.model.parts[self.part_index].name}')
            if args.track:
                self.labels[4].text = ('Base track geometry · Object instances and material effects pending' if args.track_textures else
                                      'Base track geometry · Materials and object instances pending' if args.track_mesh else
                                      'Road corridor preview · Use --track-mesh for base geometry')
            if self.body_style == 'stock' and self.body_flags is not None:
                self.labels[4].text += '   ·   Stock assembly preview'
            elif self.body_style and self.body_style != 'stock':
                self.labels[4].text += f'   ·   {self.body_style.title()} body preview'
            if self.model.warnings:
                self.labels[4].text += '   ·   Repaired invalid surface normals'
            if self.gpu_textures:
                self.labels[4].text += f'   ·   {sum(t is not None for t in self.gpu_textures)} texture pages'
            if self.texture_warning:
                self.labels[4].text += '   ·   Texture unavailable'
            if self.world_vehicle:
                self.labels[1].text = selected_vehicle.name
                self.labels[2].text = paths[self.index].parent.name
                self.labels[3].text = f'{selected_vehicle.year}   ·   {self.world_vehicle.engine.displacement_l:.2f} L   ·   {self.world_vehicle.engine.cylinders} cylinders'
                self.labels[4].text = 'Stock vehicle at track start'

        def on_draw(self):
            gl.glClearColor(0.045, 0.06, 0.08, 1.0)
            self.clear()
            if hasattr(self, 'center'):
                gl.glEnable(gl.GL_DEPTH_TEST)
                gl.glDisable(gl.GL_CULL_FACE)
                gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_LINE if self.wireframe else gl.GL_FILL)
                distance = self.radius * self.distance
                eye = self.center + Vec3(math.cos(self.pitch)*math.sin(self.yaw)*distance,
                    math.sin(self.pitch)*distance, math.cos(self.pitch)*math.cos(self.yaw)*distance)
                view = Mat4.look_at(eye, self.center, Vec3(0, 1, 0))
                projection = Mat4.perspective_projection(self.width/max(1,self.height),
                                                         0.01*self.radius, 100*self.radius, 40)
                self.program.use()
                self.program['mvp'] = projection @ view
                self.program['object_to_world'] = Mat4()
                self.program['paint'] = (0.78, 0.82, 0.87, 1.0)
                self.program['surface'] = 0
                gl.glActiveTexture(gl.GL_TEXTURE0)
                for mesh,page in self.meshes:
                    has_texture=page<len(self.gpu_textures) and self.gpu_textures[page] is not None
                    self.program['textured']=has_texture
                    if has_texture:
                        texture=self.gpu_textures[page]
                        gl.glBindTexture(texture.target,texture.id)
                    mesh.draw(gl.GL_TRIANGLES)
                if self.world_vehicle:
                    from .world import pose_matrix
                    transform = Mat4(*pose_matrix(self.drive.pose if self.drive else self.world_vehicle.pose))
                    self.program['mvp'] = projection @ view @ transform
                    self.program['object_to_world'] = transform
                    for mesh, page in self.vehicle_meshes:
                        has_texture = page < len(self.vehicle_textures) and self.vehicle_textures[page] is not None
                        self.program['textured'] = has_texture
                        if has_texture:
                            texture = self.vehicle_textures[page]
                            gl.glBindTexture(texture.target, texture.id)
                        mesh.draw(gl.GL_TRIANGLES)
                if self.drive and self.gate_mesh and not self.drive.trial.finished:
                    gate = self.drive.trial.gates[self.drive.trial.next_gate]
                    left = tuple(gate.position[i]-gate.left*gate.right[i] for i in range(3))
                    right = tuple(gate.position[i]+gate.right_limit*gate.right[i] for i in range(3))
                    left_top = (left[0], left[1]+3, left[2])
                    right_top = (right[0], right[1]+3, right[2])
                    self.gate_mesh.position[:] = (*left, *left_top, *left_top, *right_top, *right_top, *right)
                    self.program['mvp'] = projection @ view
                    self.program['object_to_world'] = Mat4()
                    self.program['textured'] = False
                    self.program['paint'] = (1, .75, .15, 1)
                    self.gate_mesh.draw(gl.GL_LINES)
                self.program.stop()
                gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_FILL)
                gl.glDisable(gl.GL_DEPTH_TEST)
            if hasattr(self, 'labels'):
                if self.hud_panels:
                    self.hud_panels[0].y = self.height-176
                    self.hud_panels[1].width = max(1, self.width-32)
                    for panel in self.hud_panels:
                        panel.draw()
                for index, label in enumerate(self.labels):
                    if index < 4:
                        label.y = self.height - (40, 83, 125, 158)[index]
                    label.draw()

        def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
            if buttons & mouse.LEFT:
                self.yaw += dx * 0.008
                self.pitch = max(-1.3, min(1.3, self.pitch + dy*0.008))

        def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
            self.distance = max(1.8, min(40, self.distance * math.exp(-scroll_y*0.1)))

        def on_key_press(self, symbol, modifiers):
            if symbol == key.ESCAPE:
                self.close()
            elif args.drive and symbol == key.R and self.drive:
                self.drive.reset()
                self.focus_start()
            elif args.drive and symbol == key.P:
                self.paused = not self.paused
                if self.paused:
                    self.labels[4].text = 'Paused · P to resume'
            elif symbol in ((key.PAGEUP, key.PAGEDOWN) if args.drive else (key.LEFT, key.RIGHT)):
                self.index = (self.index + (1 if symbol in (key.RIGHT, key.PAGEDOWN) else -1)) % len(paths)
                self.load_model()
            elif symbol == key.TAB and hasattr(self, 'model'):
                self.part_index = 0 if self.part_index is None else None
                self.rebuild()
            elif symbol in (key.BRACKETLEFT, key.BRACKETRIGHT) and hasattr(self, 'model'):
                self.part_index = ((self.part_index or 0) + (1 if symbol == key.BRACKETRIGHT else -1)) % len(self.model.parts)
                self.rebuild()
            elif symbol == key.W:
                self.wireframe = not self.wireframe
            elif symbol == key.V and not args.track:
                styles = (None, *PROFILES, *(['stock'] if selected_vehicle else []))
                self.body_style = styles[(styles.index(self.body_style)+1) % len(styles)]
                self.load_model()
            elif symbol == key.F11:
                self.set_fullscreen(not self.fullscreen)
            elif symbol == key.HOME and args.track:
                self.focus_start()
            elif symbol == key.END and args.track:
                self.follow_car = False
                self.center,self.radius=self.overview_center,self.overview_radius
                self.distance,self.pitch,self.yaw=6.5,0.3,0.65

        def capture(self, dt):
            if self.error:
                raise RuntimeError(self.error)
            checks = []
            driving_report = None
            race_report = None
            if args.verify_driving:
                from .driving import Controls
                initial = self.drive.pose
                for _ in range(180):
                    self.drive.update(1/60, Controls(throttle=1))
                accelerated = self.drive.speed
                travelled = self.drive.distance
                assert accelerated > 1 and travelled > 1 and self.drive.pose != initial
                assert all(c.gap is not None and c.gap >= .02-1e-6 for c in self.drive.contacts)
                for _ in range(120):
                    self.drive.update(1/60, Controls(brake=1))
                assert self.drive.speed == 0
                driving_report = dict(accelerated_speed_mps=accelerated, distance_m=travelled,
                                      stopped=True, physics='authored bicycle model')
                self.on_key_press(key.R, 0)
                assert self.drive.pose == initial and self.drive.speed == 0
                checks.append('driving accelerated, terrain supported, braked and reset')
            if args.verify_controls:
                original = self.index
                self.on_key_press(key.PAGEDOWN if args.drive else key.RIGHT, 0)
                assert self.index == (original+1) % len(paths) and not self.error
                checks.append('next model loaded')
                self.on_key_press(key.PAGEUP if args.drive else key.LEFT, 0)
                assert self.index == original and not self.error
                self.on_key_press(key.TAB, 0)
                assert self.part_index == 0 and self.meshes
                checks.append('part isolation rebuilt GPU geometry')
                self.on_draw()
                self.on_key_press(key.BRACKETRIGHT, 0)
                assert self.part_index == 1 % len(self.model.parts)
                self.on_key_press(key.TAB, 0)
                assert self.part_index is None
                self.on_key_press(key.W, 0)
                assert self.wireframe
                self.on_draw()
                self.on_key_press(key.W, 0)
                checks.append('wireframe rendered')
                old_distance, old_yaw = self.distance, self.yaw
                self.on_mouse_scroll(0, 0, 0, 1)
                self.on_mouse_drag(0, 0, 10, 10, mouse.LEFT, 0)
                assert self.distance < old_distance and self.yaw != old_yaw
                checks.append('orbit and zoom changed camera')
                self.set_size(1200, 800)
                self.dispatch_events()
                assert self.width == 1200
                checks.append('window resize')
                if args.track:
                    self.on_key_press(key.HOME,0)
                    assert tuple(self.center)==(self.world_vehicle.pose.position if self.world_vehicle else self.track_data.slices[0].position)
                    self.on_draw()
                    self.on_key_press(key.END,0)
                    assert self.center==self.overview_center
                    if args.track_view=='start' or world_view:self.focus_start()
                    checks.append('track start and overview camera')
                if not args.track:
                    original_style = self.body_style
                    for _ in range(5 if selected_vehicle else 4):
                        self.on_key_press(key.V, 0)
                        assert not self.error and self.meshes
                        if self.body_style and (self.body_style != 'stock' or self.body_flags is not None):
                            assert not any(p.name.startswith(':PP') for p in self.model.parts)
                    assert self.body_style == original_style
                    checks.append('body previews cycled without marker geometry')
            if args.verify_race:
                self.drive.reset()
                self.paused = False
                self.focus_start()
                self.keys.on_key_press(key.UP, 0)
                for frame in range(60*120):
                    self.update_driving(1/60)
                    if frame % 60 == 0:
                        self.on_draw()
                    if self.drive.blocked:
                        raise RuntimeError('race encountered missing wheel support')
                    if self.drive.trial.finished:
                        break
                self.keys.on_key_release(key.UP, 0)
                assert self.drive.trial.finished
                race_report = dict(seconds=self.drive.trial.elapsed, distance_m=self.drive.distance,
                                   gates=len(self.drive.trial.gates), input='held Up via key-state handler')
                checks.append('complete ordered Drag sprint through input, update and rendering')
            self.switch_to()
            self.on_draw()
            gl.glFinish()
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            pyglet.image.get_buffer_manager().get_color_buffer().save(str(args.screenshot))
            args.screenshot.with_suffix('.runtime.json').write_text(json.dumps(dict(
                platform=platform.platform(), python=platform.python_version(),
                renderer=gl.gl_info.get_renderer(), version=gl.gl_info.get_version_string(),
                model=paths[self.index].name, triangles=self.model.triangle_count,
                track=paths[self.index].parent.name if args.track else None,
                track_mesh=args.track_mesh,
                track_textures=args.track_textures,
                vehicle_id=selected_vehicle.branded_id if selected_vehicle else None,
                body_style=self.body_style,
                body_flags=self.body_flags,
                assembly_notes=self.assembly_notes,
                texture_pages=sum(t is not None for t in self.gpu_textures),
                texture_slots=len(self.gpu_textures), texture_warning=self.texture_warning,
                warnings=list(self.model.warnings), control_checks=checks,
                driving=driving_report, race=race_report), indent=2), encoding='utf-8')
            if self.world_vehicle:
                report = args.screenshot.with_suffix('.runtime.json')
                recorded = json.loads(report.read_text(encoding='utf-8'))
                recorded['world_vehicle'] = dict(pose=asdict(self.drive.pose if self.drive else self.world_vehicle.pose),
                    triangles=self.world_vehicle.model.triangle_count,
                    body_flags=self.world_vehicle.flags,
                    engine_block=asdict(self.world_vehicle.engine),
                    texture_pages=sum(t is not None for t in self.vehicle_textures),
                    contacts=[asdict(c) for c in (self.drive.contacts if self.drive else self.world_vehicle.contacts)],
                    assembly_notes=self.world_vehicle.notes)
                report.write_text(json.dumps(recorded, indent=2), encoding='utf-8')
            print(f'Rendered {paths[self.index].name}: {self.model.triangle_count} triangles to {args.screenshot}')
            self.close()

        def on_close(self):
            pyglet.clock.unschedule(self.update_driving)
            if not args.screenshot:
                try:
                    settings.save(dict(data_root=str(assets.root), model=previous.get('model', '32ford.viv')
                                       if args.track else paths[self.index].name))
                except OSError as error:
                    print(f'Settings could not be saved: {error}', file=sys.stderr)
            return super().on_close()

    try:
        Garage()
        pyglet.app.run(interval=1/60)
    except (pyglet.window.NoSuchConfigException, pyglet.gl.ContextException) as error:
        parser.exit(1, f'OpenGL 3.3 context unavailable: {error}\n')


if __name__ == '__main__':
    main()
