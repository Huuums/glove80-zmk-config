import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from resolve_helpers import resolve

DTS = '''
helper: helper_node {
 bindings = < &macro_release &kp 0x700e0 &kp 0x700e1 &kp 0x700e2 &kp 0x700e3 &kp 0x700e4 &kp 0x700e5 &kp 0x700e6 &kp 0x700e7 >, < &macro_tap &kp 0x70006 >, < &macro_param_1to1 >, < &macro_tap &kp 0x0 >;
};
layer_Test { bindings = < &helper 0x70005 &kp 0x7000b >; };
'''
LAYOUT = {'layer_names': ['Test'], 'layers': [[{'decoration': {'label': 'Tap'}}, {'decoration': {'label': 'Tap'}}]]}

class HelperTests(unittest.TestCase):
    def test_compiled_sequence_and_direct_key(self):
        bindings = resolve(LAYOUT, DTS)
        self.assertEqual(bindings['0:0'], {'codes': [0x70006, 0x70005], 'clearsModifiers': True})
        self.assertEqual(bindings['0:1'], {'codes': [0x7000b], 'clearsModifiers': False})

    def test_unknown_macro_is_not_guessed(self):
        bindings = resolve(LAYOUT, DTS.replace('&macro_param_1to1', '&unknown_behavior'))
        self.assertNotIn('0:0', bindings)

    def test_incomplete_modifier_release_is_not_assumed(self):
        bindings = resolve(LAYOUT, DTS.replace(' &kp 0x700e7', ''))
        self.assertNotIn('0:0', bindings)

    def test_different_layout_shape_rejected(self):
        with self.assertRaises(ValueError):
            resolve(LAYOUT, DTS.replace('&kp 0x7000b', ''))
