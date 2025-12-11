import unittest
from crp_desktop.parser import extract_fields_from_block

class ParserTests(unittest.TestCase):
    def test_basic_packet(self):
        sample = (
            "\x02\n! 6.23\n2 4.5\n3 13.2\nK 0.8\n$FB MyInstrument\n$FE v1\n\x03"
        )
        parsed = extract_fields_from_block(sample)
        self.assertIn('WBC', parsed)
        self.assertIn('RBC', parsed)
        self.assertIn('HGB', parsed)
        self.assertEqual(parsed.get('CRP'), '0.8 mg/dL')
        self.assertEqual(parsed.get('InstrumentName'), 'MyInstrument')

if __name__ == "__main__":
    unittest.main()
