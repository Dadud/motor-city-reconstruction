"""Single-owner control flow for recovered room disconnect 0x44d750.

The driver supplies observed images and performs explicit actions. This class
does not run host callbacks, create threads, send packets or invent timeouts.
"""
from dataclasses import dataclass
import struct

from client.room_disconnect import ROOM_DISCONNECT_MIN_SIZE, prepare_room_disconnect


def _image(value):
    if not isinstance(value, bytes) or not ROOM_DISCONNECT_MIN_SIZE <= len(value) <= 65536:
        raise ValueError('expected bounded complete room image')
    return value


def _i32(value):
    if type(value) is not int or not -0x80000000 <= value <= 0x7fffffff:
        raise ValueError('expected signed int32 result')
    return value


@dataclass(frozen=True)
class RoomDisconnectAction:
    kind: str
    owner_offset: int | None = None
    argument: bytes | None = None
    tracked: bool = False
    operation_id: int | None = None
    result: int | None = None


class RoomDisconnectFlow:
    """Consume one observation per requested action, in original call order.

    Initial container resets precede connected/pending inspection. A pending
    loop reads connected again only after pending reaches zero. Settings reset
    before enqueue; tracked completion is queried before the first app pump.
    """
    def __init__(self, room_image: bytes, *, wait_for_completion: bool):
        if type(wait_for_completion) is not bool:
            raise ValueError('wait switch must be boolean')
        self._image = _image(room_image)
        self._wait = wait_for_completion
        self._phase = 'reset_first'
        self._preparation = None
        self._operation_id = None
        self._result = None

    @property
    def room_image(self):
        return self._image

    @property
    def action(self):
        if self._phase in ('reset_first', 'reset_second'):
            return RoomDisconnectAction('reset_container', 0x2e0 if self._phase == 'reset_first' else 0x1fc)
        if self._phase == 'yield_pending':
            return RoomDisconnectAction('yield_pending')
        if self._phase == 'enqueue':
            return RoomDisconnectAction('enqueue', 12, self._preparation.argument, self._preparation.tracked)
        if self._phase == 'query':
            return RoomDisconnectAction('query_completion', 12, operation_id=self._operation_id)
        if self._phase == 'pump':
            return RoomDisconnectAction('pump_application')
        return RoomDisconnectAction('complete', result=self._result)

    def _require(self, *phases):
        if self._phase not in phases:
            raise ValueError('observation does not match requested disconnect action')

    def _observe(self, room_image):
        image = _image(room_image)
        if len(image) != len(self._image):
            raise ValueError('observed room image size changed')
        self._image = image

    def _prepare(self):
        self._preparation = prepare_room_disconnect(self._image, wait_for_completion=self._wait)
        self._image = self._preparation.room_image
        if self._preparation.argument is None:
            self._result, self._phase = 0, 'complete'
        else:
            self._phase = 'enqueue'

    def container_reset(self, observed_image: bytes):
        self._require('reset_first', 'reset_second')
        self._observe(observed_image)
        if self._phase == 'reset_first':
            self._phase = 'reset_second'
        elif (struct.unpack_from('<H', self._image, 0xec)[0] != 0 and
              struct.unpack_from('<I', self._image, 0x3a8)[0] != 0):
            self._phase = 'yield_pending'
        else:
            self._prepare()

    def pending_yielded(self, observed_image: bytes):
        self._require('yield_pending')
        self._observe(observed_image)
        if struct.unpack_from('<I', self._image, 0x3a8)[0] == 0:
            self._prepare()

    def enqueued(self, record_operation_id: int | None = None):
        """Supply the ID written into the tracked record, not enqueue's EAX.

        ID zero causes the original query's C++ throw. This authored boundary
        rejects it before querying; untracked record headers are not consumed.
        """
        self._require('enqueue')
        if self._preparation.tracked:
            if type(record_operation_id) is not int or not 1 <= record_operation_id <= 0xffffffff:
                raise ValueError('tracked disconnect needs the record nonzero uint32 operation ID')
            self._operation_id, self._phase = record_operation_id, 'query'
        else:
            self._result, self._phase = 0, 'complete'

    def completion_queried(self, result: int | None):
        self._require('query')
        if result is None:
            self._phase = 'pump'
        else:
            self._result = _i32(result)
            self._phase = 'complete'

    def application_pumped(self, result: int):
        self._require('pump')
        if _i32(result) != 0:
            self._result, self._phase = -51, 'complete'
        else:
            self._phase = 'query'
