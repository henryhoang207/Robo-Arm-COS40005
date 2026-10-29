import unittest
from protocol import parse_action,ProtocolError

L=[(-1.8,1.8),(-1.7,1.7),(-1.6,1.6),(-1.5,1.5),(-2.7,2.8),(-.17,1.7)]
class TestProtocol(unittest.TestCase):
    def test_accept(self):
        result=parse_action({'type':'ACTION','sequence_id':2,'joint_targets':[0,0,0,0,0,0]},L,1)
        self.assertEqual(result.duration,2)
    def test_replay(self):
        with self.assertRaises(ProtocolError):parse_action({'type':'ACTION','sequence_id':1,'joint_targets':[0]*6},L,1)
    def test_out_of_range(self):
        with self.assertRaises(ProtocolError):parse_action({'type':'ACTION','sequence_id':3,'joint_targets':[10,0,0,0,0,0]},L,1)
    def test_nonfinite(self):
        with self.assertRaises(ProtocolError):parse_action({'type':'ACTION','sequence_id':3,'joint_targets':[float('nan'),0,0,0,0,0]},L,1)
    def test_bad_duration(self):
        with self.assertRaises(ProtocolError):parse_action({'type':'ACTION','sequence_id':3,'joint_targets':[0]*6,'duration':0},L,1)
    def test_length(self):
        with self.assertRaises(ProtocolError):parse_action({'type':'ACTION','sequence_id':3,'joint_targets':[0]*5},L,1)
if __name__=='__main__':unittest.main()
