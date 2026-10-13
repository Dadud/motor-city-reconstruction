"""Read-only stock vehicle joins from the local Jet database.

Database identities and references are retained. Configuration flags are exposed
without interpreting them as visibility, and this module does not place parts.
"""
from dataclasses import dataclass
import logging
import sys
import math
import struct


def validated_rows(name, columns, declared, key=None):
    lengths = {len(value) for value in columns.values()}
    if lengths != {declared}:
        raise ValueError(f'{name}: parsed column counts differ from declared rows')
    rows = [dict(zip(columns, values)) for values in zip(*columns.values())]
    if key:
        identifiers = [row[key] for row in rows]
        if None in identifiers or len(set(identifiers)) != declared:
            raise ValueError(f'{name}: missing or duplicate {key}')
    return rows


@dataclass(frozen=True)
class StockPart:
    branded_id: int
    part_type_id: int
    abstract_type_id: int
    attachment_id: int
    attachment: str
    name: str
    filename: str | None
    config_default: int
    physics_default: int


@dataclass(frozen=True)
class Vehicle:
    branded_id: int
    name: str
    year: int
    retail_price: int
    parts: tuple[StockPart, ...]

    @property
    def body_filename(self):
        # Abstract type 20001 is Body, corroborated by its EAPT database label.
        bodies = {part.filename for part in self.parts
                  if part.abstract_type_id == 20001 and part.filename}
        if len(bodies) != 1:
            raise ValueError(f'vehicle {self.branded_id}: expected one stock body asset')
        return next(iter(bodies))


class Catalogue:
    def __init__(self, tables):
        from .physics_data import decode_physics_table
        physics=tables.get('Physics', [])
        self.owned_physics_rows = {(row['PartTypeID'],row['Ordinal']):dict(row) for row in physics}
        self.physics_duty = {(row['PartTypeID'], row['Ordinal']): row.get('DutyRating')
                             for row in physics}
        self.physics=decode_physics_table({key:[row[key] for row in physics] for key in physics[0]}) if physics else {}
        self.branded = self._index(tables['BrandedPart'], 'BrandedPartID')
        self.types = self._index(tables['PartType'], 'PartTypeID')
        self.abstract = self._index(tables['AbstractPartType'], 'AbstractPartTypeID')
        self.models = self._index(tables['Model'], 'ModelID')
        self.attachments = self._index(tables['AttachmentPoint'], 'AttachmentPointID')
        self.vehicles = self._index(tables['StockVehicleAttributes'], 'BrandedPartID')
        self.assemblies = {}
        for row in tables['StockAssembly']:
            self.assemblies.setdefault(row['ParentBrandedPartID'], []).append(row)

    @staticmethod
    def _index(rows, key):
        result = {}
        for row in rows:
            identifier = row[key]
            if identifier is None or identifier in result:
                raise ValueError(f'missing or duplicate {key}')
            result[identifier] = row
        return result

    def vehicle(self, identifier):
        try:
            stock = self.vehicles[identifier]
            branded = self.branded[identifier]
            model = self.models[branded['ModelID']]
            parts = []
            for row in self.assemblies.get(identifier, []):
                child = self.branded[row['ChildBrandedPartID']]
                kind = self.types[child['PartTypeID']]
                abstract = self.abstract[kind['AbstractPartTypeID']]
                child_model = self.models[child['ModelID']]
                attachment = self.attachments[row['AttachmentPointID']]
                parts.append(StockPart(child['BrandedPartID'], kind['PartTypeID'],
                    kind['AbstractPartTypeID'], row['AttachmentPointID'],
                    attachment['AttachmentPoint'], child_model['EModel'] or kind['PartType'],
                    kind['PartFilename'] or abstract['PartFilename'],
                    row['ConfigDefault'], row['PhysicsDefault']))
            year = int(str(branded['MfgDate'])[:4])
            return Vehicle(identifier, model['Debug_String'] or model['EModel'],
                           year, stock['RetailPrice'], tuple(parts))
        except KeyError as error:
            raise ValueError(f'vehicle {identifier}: missing database reference {error}') from error

    def owned_part_metadata(self, part):
        """BrandPart_SelectE join for an actual instance, including modified parts.

        No StockAssembly replacement is made. Native query selection order
        identifies metadata; instance damage/wear remain in the supplied part.
        """
        from .owned_parts import OwnedPart, OwnedPartMetadata
        if not isinstance(part,OwnedPart):
            raise ValueError('expected an owned-part instance')
        part.native_seed()
        try:
            branded = self.branded[part.branded_part_id]
            kind = self.types[branded['PartTypeID']]
            model = self.models[branded['ModelID']]
            def native_integer(value):
                return 0 if value is None else value
            return OwnedPartMetadata(native_integer(kind['AbstractPartTypeID']),kind['PartTypeID'],
                native_integer(branded['RetailPrice']),native_integer(branded['MaxItemWear']),
                0 if branded['MfgDate'] is None else int(str(branded['MfgDate'])[:4]),native_integer(kind['PartGradeID']),
                native_integer(branded['EngineBlockFamilyID']),native_integer(model['BrandID']),kind['PartType'],
                model['EModel'],model['EShortModel'],model['EExtraInfo'],kind['PartFilename'])
        except (KeyError,TypeError,ValueError) as error:
            raise ValueError('owned part has missing or invalid branded metadata') from error

    def owned_part_intermediate(self, part, *, text_encoding):
        """Join instance metadata and Physics_Select ordinal 1.

        Family/type-specific text overrides and later native calculations are
        not yet included; this returns an intermediate slot, not a playable car.
        A missing ordinal-1 row reproduces the native cleared physics record.
        """
        from .owned_physics import apply_owned_physics
        metadata = self.owned_part_metadata(part)
        slot = metadata.apply_numeric_fields(part)
        slot = metadata.apply_text_fields(slot,text_encoding=text_encoding)
        if metadata.part_type_id == 0:
            return slot
        row = self.owned_physics_rows.get((metadata.part_type_id,1))
        return apply_owned_physics(slot,row,text_encoding=text_encoding)

    def tire_dimensions(self, vehicle):
        """Resolve stock wheel/axle attachments with unambiguous physics rows.

        PhysicsDefault is retained as a flag, never treated as an ordinal.
        Explicit wheel attachments take precedence over their axle attachment.
        """
        from .tires import TireDimensions
        return self._wheel_physics(vehicle,110001,'tire',TireDimensions)

    def suspension(self,vehicle):
        """Resolve stock springs and shocks independently for each wheel."""
        from .suspension import Spring,Shock
        springs=self._wheel_physics(vehicle,12001,'spring',Spring)
        shocks=self._wheel_physics(vehicle,11001,'shock',Shock)
        return {key:(springs[key],shocks[key]) for key in springs}

    def engine_block(self, vehicle):
        """Resolve one stock engine block; PhysicsDefault is not an ordinal."""
        from .engine import EngineBlock
        parts = [p for p in vehicle.parts if p.abstract_type_id == 160001]
        if len(parts) != 1:
            raise ValueError(f'vehicle {vehicle.branded_id}: ambiguous or missing engine block')
        records = [record for (kind, _), record in self.physics.items()
                   if kind == parts[0].part_type_id]
        if len(records) != 1:
            raise ValueError(f'vehicle {vehicle.branded_id}: ambiguous or missing engine block physics')
        return EngineBlock.from_physics(records[0])

    def cylinder_head(self, vehicle):
        """Resolve the stock Cylinder Head (APT 1000001) without guessing ordinals."""
        from .engine import CylinderHead
        parts = [p for p in vehicle.parts if p.abstract_type_id == 1000001]
        if len(parts) != 1:
            raise ValueError(f'vehicle {vehicle.branded_id}: ambiguous or missing cylinder head')
        records = [record for (kind, _), record in self.physics.items()
                   if kind == parts[0].part_type_id]
        if len(records) != 1:
            raise ValueError(f'vehicle {vehicle.branded_id}: ambiguous or missing cylinder head physics')
        return CylinderHead.from_physics(records[0])

    def engine_family(self, vehicle):
        """Family metadata: BrandPart_SelectE column 12 -> +0x203 -> +0x53b.

        REA 097/121/191 and the saved MSysQueries selection order establish
        this path. Physics Val5 is not used as a substitute.
        """
        parts = [p for p in vehicle.parts if p.abstract_type_id == 160001]
        if len(parts) != 1:
            raise ValueError(f'vehicle {vehicle.branded_id}: ambiguous or missing engine block')
        row = self.branded.get(parts[0].branded_id, {})
        family = row.get('EngineBlockFamilyID')
        if type(family) is not int or not 1 <= family <= 26:
            raise ValueError(f'vehicle {vehicle.branded_id}: invalid engine family metadata')
        return family

    def engine_flow_template_id(self, vehicle):
        """Select the native head-flow template using the actual stock family."""
        return self.cylinder_head(vehicle).flow_template_id(
            self.engine_block(vehicle).bore_m, self.engine_family(vehicle))

    def camshaft(self, vehicle):
        """Resolve stock Camshaft (APT 1100001) with an unambiguous physics row."""
        from .engine import Camshaft
        parts = [p for p in vehicle.parts if p.abstract_type_id == 1100001]
        if len(parts) != 1:
            raise ValueError(f'vehicle {vehicle.branded_id}: ambiguous or missing camshaft')
        records = [record for (kind, _), record in self.physics.items()
                   if kind == parts[0].part_type_id]
        if len(records) != 1:
            raise ValueError(f'vehicle {vehicle.branded_id}: ambiguous or missing camshaft physics')
        return Camshaft.from_physics(records[0])

    def valve_train(self, vehicle):
        """Resolve stock Valve Train (APT 1200001) without ordinal assumptions."""
        from .engine import ValveTrain
        parts = [p for p in vehicle.parts if p.abstract_type_id == 1200001]
        if len(parts) != 1:
            raise ValueError(f'vehicle {vehicle.branded_id}: ambiguous or missing valve train')
        records = [record for (kind, _), record in self.physics.items()
                   if kind == parts[0].part_type_id]
        if len(records) != 1:
            raise ValueError(f'vehicle {vehicle.branded_id}: ambiguous or missing valve-train physics')
        return ValveTrain.from_physics(records[0])

    def stock_dyno_record(self, vehicle, templates):
        """Portable core dyno inputs; see _stock_dyno_buffers for limitations."""
        return self._stock_dyno_buffers(vehicle, templates)[0]

    def stock_dyno_assembled(self, vehicle, templates):
        """Recovered assembled fields for comparing builders in the CPU oracle.

        This is a partial structure, not a complete native vehicle assembly.
        """
        return self._stock_dyno_buffers(vehicle, templates)[1]

    def _stock_dyno_buffers(self, vehicle, templates):
        """Assemble recovered naturally aspirated core inputs, not final torque.

        REA 198/228–237. Special carburetor/boost paths are rejected. Worn-part
        overrides and full native compatibility validation remain unimplemented.
        The record is suitable for the development oracle; the client still
        needs a portable implementation of the full solver and curve finalizer.
        """
        from .dyno import build_dyno_record
        def component(abstract_type, count, optional=False):
            parts = [p for p in vehicle.parts if p.abstract_type_id == abstract_type]
            if optional and not parts:
                return None
            if len(parts) != 1:
                raise ValueError(f'vehicle {vehicle.branded_id}: ambiguous/missing dyno component {abstract_type}')
            records = [r for (kind, _), r in self.physics.items() if kind == parts[0].part_type_id]
            if len(records) != 1 or len(records[0].values) < count:
                raise ValueError(f'vehicle {vehicle.branded_id}: ambiguous/incomplete dyno physics {abstract_type}')
            return records[0]
        if any(p.abstract_type_id in (350001, 360001) for p in vehicle.parts):
            raise ValueError('stock dyno boost/nitrous branches are not implemented')
        intake = component(320001, 3)
        carb = component(330001, 3)
        exhaust = component(280001, 3)
        air = component(340001, 0, True)
        muffler = component(300001, 2, True)
        scoop = component(340333, 1, True)
        intake_type, intake_config, intake_flow = intake.values[:3]
        exhaust_type, exhaust_config, exhaust_flow = exhaust.values[:3]
        carb_type, carb_flow, capacity = carb.values[:3]
        if not (intake.mass is not None and 5 <= intake.mass <= 50 and
                0 <= round(intake_type) <= 2 and 0 <= round(intake_config) <= 9 and
                .9 <= intake_flow <= 1.1 and exhaust.mass is not None and
                5 <= exhaust.mass <= 50 and 0 <= round(exhaust_type) <= 3 and
                0 <= round(exhaust_config) <= 9 and .9 <= exhaust_flow <= 1.1 and
                carb.mass is not None and 1 <= carb.mass <= 10 and
                0 <= round(carb_type) <= 5 and .9 <= carb_flow <= 1.1 and
                100 <= capacity <= 1600 and capacity == int(capacity)):
            raise ValueError('unsupported stock dyno intake/exhaust/carb fields')
        air_loss = 0
        if air:
            duty = self.physics_duty.get((air.part_type_id, air.ordinal))
            if duty is None or not math.isfinite(duty):
                raise ValueError('missing air-cleaner duty rating')
            air_loss = min(max((duty+1)*.0025, .0025), .01)
        exhaust_type = round(exhaust_type)
        muffler_gain = 0
        if muffler and round(muffler.values[1]) == 1:
            word = (0x3c4ccccd, 0x3c75c28f, 0x3cc49ba6, 0x3c83126f)[exhaust_type]
            muffler_gain = struct.unpack('<f', struct.pack('<I', word))[0]
        head = self.cylinder_head(vehicle)
        def f32(value):
            return struct.unpack('<f', struct.pack('<f', value))[0]
        modifier = (f32(head.flow_factor)-f32(air_loss)+f32(muffler_gain)+
                    (f32(scoop.values[0]) if scoop else 0))
        template = templates[self.engine_flow_template_id(vehicle)].scaled(modifier)
        mode = (1, 2, 3 if muffler and muffler.mass else 4,
                5 if muffler and muffler.mass else 6)[exhaust_type]
        block = self.engine_block(vehicle)
        cam = self.camshaft(vehicle)
        train = self.valve_train(vehicle)
        record = build_dyno_record(block, head, cam, train, template,
            intake_mode=round(intake_type)+1, intake_flow=intake_flow,
            exhaust_mode=mode, exhaust_flow=exhaust_flow,
            carb_capacity=math.trunc(f32(capacity)*f32(carb_flow)),
            carb_code=2 if round(carb_type) in (0, 1) else 4)
        assembled = bytearray(0x820)
        for offset, value in ((0x3ac, round(intake_type)), (0x3c8, round(carb_type)),
                              (0x43c, block.cylinders), (0x440, self.engine_family(vehicle)),
                              (0x50c, head.head_type), (0x510, head.port_type),
                              (0x534, cam.cam_type), (0x564, train.train_type),
                              (0x57c, exhaust_type)):
            struct.pack_into('<i', assembled, offset, value)
        for offset, value in ((0x3b4, intake_flow), (0x3cc, capacity), (0x3d0, carb_flow),
                              (0x3f4, air_loss), (0x400, scoop.values[0] if scoop else 0),
                              (0x430, block.bore_m), (0x434, block.stroke_m),
                              (0x54, head.compression_ratio), (0x518, head.flow_factor),
                              (0x524, head.intake_valve_mm), (0x528, head.exhaust_valve_mm),
                              (0x544, cam.intake_lift_mm), (0x548, cam.exhaust_lift_mm),
                              (0x54c, cam.timing_fields[0]), (0x550, cam.timing_fields[1]),
                              (0x554, cam.timing_fields[2]), (0x558, cam.timing_fields[3]),
                              (0x568, train.lift_factor), (0x584, exhaust_flow),
                              (0x5a0, muffler.mass if muffler and muffler.mass else 0),
                              (0x5b0, muffler_gain)):
            struct.pack_into('<f', assembled, offset, value)
        return record, bytes(assembled)

    def _wheel_physics(self,vehicle,abstract_type,label,factory):
        result={}
        for wheel,side,axle in (('LF',1,10),('RF',2,10),('LR',3,11),('RR',4,11)):
            parts=[p for p in vehicle.parts if p.abstract_type_id==abstract_type]
            matches=[p for p in parts if p.attachment_id==side]
            if not matches:
                matches=[p for p in parts if p.attachment_id==axle]
            if len(matches)!=1:
                raise ValueError(f'vehicle {vehicle.branded_id}: ambiguous or missing {wheel} {label}')
            records=[record for (kind,_),record in self.physics.items() if kind==matches[0].part_type_id]
            if len(records)!=1:
                raise ValueError(f'vehicle {vehicle.branded_id}: ambiguous or missing {wheel} {label} physics')
            result[wheel]=factory.from_physics(records[0])
        return result

    @classmethod
    def load(cls, path):
        try:
            from access_parser import AccessParser
        except ImportError as error:
            raise ValueError('stock catalogue requires: pip install -e ".[catalogue]"') from error
        # No DAO, ODBC, COM or database writes: the parser consumes file bytes.
        class MetadataDiagnostics(logging.Filter):
            count = 0

            def filter(self, record):
                if record.getMessage() == 'Error while parsing MSysObjects table chunk.':
                    self.count += 1
                    return False
                return True

        diagnostics = MetadataDiagnostics()
        logger = logging.getLogger('access_parser')
        logger.addFilter(diagnostics)
        try:
            database = AccessParser(str(path))
        finally:
            logger.removeFilter(diagnostics)
        if diagnostics.count:
            print(f'Database metadata: {diagnostics.count} unsupported system-property chunks; '
                  'stock table row counts will be checked.', file=sys.stderr)
        tables = {}
        keys = {'BrandedPart': 'BrandedPartID', 'PartType': 'PartTypeID',
                'AbstractPartType': 'AbstractPartTypeID', 'Model': 'ModelID',
                'AttachmentPoint': 'AttachmentPointID',
                'StockVehicleAttributes': 'BrandedPartID', 'StockAssembly': None,
                'Physics': None}
        for name, key in keys.items():
            table = database.get_table(name)
            if table is None:
                raise ValueError(f'missing database table: {name}')
            tables[name] = validated_rows(name, table.parse(), table.table_header.number_of_rows, key)
        return cls(tables)
