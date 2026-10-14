"""Single-owner game-start wait control recovered from original 0x450db0.

Actions describe local worker and room-cache operations, not network packets.
The driver supplies observations; this class starts no thread and sends nothing.
"""
from dataclasses import dataclass
import struct


def _image(value):
    if not isinstance(value, bytes) or not 0x5d0 <= len(value) <= 65536:
        raise ValueError('expected bounded complete network-owner image')
    return value


def _result(value):
    if type(value) is not int or not -0x80000000 <= value <= 0x7fffffff:
        raise ValueError('expected signed int32 observed result')
    return value


@dataclass(frozen=True)
class GameStartAction:
    kind: str
    owner_offset: int | None = None
    argument: bytes | None = None
    operation_id: int | None = None
    channel_id: int | None = None
    result: int | None = None


class GameStartFlow:
    def __init__(self, network_image: bytes):
        self._image = _image(network_image)
        self._argument = struct.pack('<II', struct.unpack_from('<I', network_image, 0x5cc)[0],
                                     struct.unpack_from('<I', network_image, 0x160)[0])
        self._phase = 'enqueue'
        self._operation_id = None
        self._result = None

    @property
    def network_image(self):
        return self._image

    @property
    def action(self):
        if self._phase == 'enqueue':
            return GameStartAction('enqueue_task_5', 12, self._argument)
        if self._phase == 'query':
            return GameStartAction('query_completion', 12, operation_id=self._operation_id)
        if self._phase in ('pump_completion', 'pump_status'):
            return GameStartAction('pump_application')
        if self._phase == 'status':
            return GameStartAction('query_room_status', 0x458,
                                   channel_id=struct.unpack_from('<I', self._image, 0x160)[0])
        return GameStartAction('complete', result=self._result)

    def _require(self, *phases):
        if self._phase not in phases:
            raise ValueError('observation does not match requested game-start action')

    def _finish(self, result):
        self._result, self._phase = result, 'complete'

    def enqueued(self, record_operation_id):
        self._require('enqueue')
        if type(record_operation_id) is not int or not 1 <= record_operation_id <= 0xffffffff:
            raise ValueError('tracked start needs the record nonzero uint32 operation ID')
        self._operation_id, self._phase = record_operation_id, 'query'

    def completion_queried(self, result: int | None):
        self._require('query')
        if result is None:
            self._phase = 'pump_completion'
        elif _result(result) < 0:
            self._finish(result)
        else:
            # Original initializes temporary settings, then pumps BEFORE lookup.
            self._phase = 'pump_status'

    def application_pumped(self, result: int, *, observed_network_image: bytes | None = None):
        self._require('pump_completion', 'pump_status')
        result = _result(result)
        if observed_network_image is not None:
            image = _image(observed_network_image)
            if len(image) != len(self._image):
                raise ValueError('observed network-owner image size changed')
            self._image = image
        if result != 0:
            self._finish(-51)
        else:
            self._phase = 'query' if self._phase == 'pump_completion' else 'status'

    def room_status_queried(self, status: int | None):
        self._require('status')
        if status is None:
            self._finish(-7)
        else:
            if type(status) is not int or not 0 <= status <= 255:
                raise ValueError('expected room-status byte or missing lookup')
            if status in (4, 8):
                self._finish(0 if status == 4 else -20)
            else:
                self._phase = 'pump_status'
