"""Bounded original post-login page assembly, with explicit unwritten slots."""
from dataclasses import dataclass, field
import struct
from client.mcots_data_response import MCOTSDataReply, _REPLIES, _FIXED_SIZES


def _clear_duplicate_ids(records):
    seen = set()
    result = []
    for record in records:
        identifier = struct.unpack_from('<I', record)[0]
        if identifier and identifier in seen:
            record = bytes(4)+record[4:]
        elif identifier:
            seen.add(identifier)
        result.append(record)
    return tuple(result)


@dataclass(frozen=True)
class MCOTSDataResult:
    request_operation: int
    records: tuple[bytes | None, ...] = field(repr=False)
    extensions: tuple[bytes, ...] = field(repr=False)


class MCOTSDataAssembler:
    def __init__(self, request_operation, transaction_value, *, max_bytes=16*1024*1024,
                 max_pages=1024):
        if type(request_operation) is not int or request_operation not in _REPLIES:
            raise ValueError('unsupported post-login request operation')
        if type(transaction_value) is not int or not 0 <= transaction_value <= 0xffffffff:
            raise ValueError('expected uint32 pending transaction')
        if type(max_bytes) is not int or max_bytes < 118:
            raise ValueError('expected positive bounded result capacity')
        if type(max_pages) is not int or max_pages < 1:
            raise ValueError('expected positive page limit')
        self.operation, self.transaction = request_operation, transaction_value
        self.max_bytes, self.max_pages = max_bytes, max_pages
        self._records, self._extensions = [], []
        self._pages = self._size = 0
        self.complete = False

    def feed(self, frame):
        """Return a result on the final page; invalid input leaves state intact.

        0x16c overwrites from the base, despite increasing the total count.
        Slots never written by any page are None, because the original heap
        allocation is not initialized. Never invent zero-filled account data.
        """
        if self.complete:
            raise ValueError('MCOTS data result already complete')
        page = MCOTSDataReply.from_frame(frame, transaction_value=self.transaction,
                                        request_operation=self.operation)
        stride = _REPLIES[self.operation][1] or _FIXED_SIZES[self.operation]
        size = self._size+len(page.records)*stride+len(page.extension)
        if size > self.max_bytes or self._pages >= self.max_pages:
            raise ValueError('MCOTS data result exceeds configured resource limit')
        records = self._records+list(page.records)
        if self.operation == 0x16b:
            records = self._records+[None]*len(page.records)
            records[:len(page.records)] = page.records
        extensions = self._extensions+[page.extension]
        result = None
        if not page.more:
            if self.operation == 0x144:
                records = list(_clear_duplicate_ids(records))
            result = MCOTSDataResult(self.operation, tuple(records), tuple(extensions))
        self._records, self._extensions = records, extensions
        self._size, self._pages = size, self._pages+1
        self.complete = result is not None
        return result
