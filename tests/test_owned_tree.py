import struct
import unittest
from types import SimpleNamespace
from client.owned_parts import OwnedInstanceCache
from client.owned_tree import discover_owned_tree


def row(identifier,parent,brand,attach=10):
    return dict(PartID=identifier,ParentPartID=parent,BrandedPartID=brand,
                AttachmentPointID=attach,PercentDamage=0,ItemWear=0,RepairCost=0,ScrapValue=0)


class OwnedTreeTests(unittest.TestCase):
    def catalogue(self):
        return SimpleNamespace(branded={10:dict(PartTypeID=100),11:dict(PartTypeID=101),12:dict(PartTypeID=102)},
            types={100:dict(AbstractPartTypeID=1001,PartFilename='chassis'),
                   101:dict(AbstractPartTypeID=160001,PartFilename='engine'),
                   102:dict(AbstractPartTypeID=20001,PartFilename='body')})

    def test_breadth_first_discovery_expands_only_original_assembly_types(self):
        cache = OwnedInstanceCache([row(2,1,10),row(3,1,11),row(4,2,12),row(5,3,12)])
        result = discover_owned_tree(1,cache,self.catalogue(),text_encoding='cp1252')
        self.assertEqual(result.queried_parent_ids,(1,2))
        self.assertEqual(tuple(struct.unpack_from('<I',s,0x5f8)[0] for s in result.slots),(1,2,3,4))
        self.assertEqual(struct.unpack_from('<i',result.slots[1],0x61c)[0],10)
        self.assertEqual(result.slots[1][0x387:0x38f],b'chassis\0')
        self.assertEqual(result.slots[1][0x1e3:0x1e7],bytes(4))

    def test_inner_join_excludes_missing_references_and_null_parent_does_not_match(self):
        cache = OwnedInstanceCache([row(2,1,99),row(3,None,10)])
        result = discover_owned_tree(1,cache,self.catalogue(),text_encoding='cp1252')
        self.assertEqual(len(result.slots),1)
        self.assertEqual(result.queried_parent_ids,(1,))

    def test_cycles_limits_and_unterminated_source_buffers_fail(self):
        cache = OwnedInstanceCache([row(2,1,10),row(1,2,10)])
        with self.assertRaises(ValueError):
            discover_owned_tree(1,cache,self.catalogue(),text_encoding='cp1252')
        cache = OwnedInstanceCache([row(2,1,10)])
        with self.assertRaises(ValueError):
            discover_owned_tree(1,cache,self.catalogue(),text_encoding='cp1252',max_parts=1)
        catalogue = self.catalogue()
        catalogue.types[100]['PartFilename'] = 'x'*9
        with self.assertRaises(ValueError):
            discover_owned_tree(1,cache,catalogue,text_encoding='cp1252')
