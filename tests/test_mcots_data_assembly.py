import struct
import unittest
from client.mcots_data_assembly import MCOTSDataAssembler
from client.mcots_framing import MCOTSFrame


def page(opcode, records, more=0, transaction=7, tail=b''):
    return MCOTSFrame(transaction,0,struct.pack('<HHB',opcode,len(records),more)+b''.join(records)+tail)


class DataAssemblyTests(unittest.TestCase):
    def test_duplicate_ids_are_cleared_only_at_completion(self):
        def record(identifier, fill):
            return struct.pack('<I',identifier)+bytes([fill])*565
        first, duplicate, zero = record(42,1), record(42,2), record(0,3)
        assembly = MCOTSDataAssembler(0x144,7)
        self.assertIsNone(assembly.feed(page(0x145,[first],255,tail=b'a')))
        result = assembly.feed(page(0x145,[duplicate,zero],tail=b'b'))
        self.assertEqual(result.records,(first,bytes(4)+duplicate[4:],zero))
        self.assertEqual(result.extensions,(b'a',b'b'))
        with self.assertRaises(ValueError):
            assembly.feed(page(0x145,[]))

    def test_overwrite_keeps_old_tail_and_marks_unwritten_slots(self):
        assembly = MCOTSDataAssembler(0x16b,7)
        first, old_tail, latest = b'a'*516,b'b'*516,b'c'*516
        self.assertIsNone(assembly.feed(page(0x16c,[first,old_tail],1)))
        result = assembly.feed(page(0x16c,[latest]))
        self.assertEqual(result.records,(latest,old_tail,None))

    def test_invalid_or_excessive_page_does_not_poison_previous_pages(self):
        assembly = MCOTSDataAssembler(0x142,7,max_bytes=118,max_pages=2)
        self.assertIsNone(assembly.feed(page(0x143,[b'12345678'],1)))
        for invalid in (page(0x143,[b'abcdefgh'],transaction=8),
                        page(0x143,[b'x'*8]*14)):
            with self.assertRaises(ValueError):
                assembly.feed(invalid)
        result = assembly.feed(page(0x143,[b'abcdefgh']))
        self.assertEqual(result.records,(b'12345678',b'abcdefgh'))
        capped = MCOTSDataAssembler(0x142,7,max_pages=1)
        capped.feed(page(0x143,[],1))
        with self.assertRaises(ValueError):
            capped.feed(page(0x143,[]))
