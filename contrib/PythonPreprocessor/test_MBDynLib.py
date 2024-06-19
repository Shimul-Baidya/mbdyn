from io import StringIO
import unittest

import MBDynLib as l

try:
    import pydantic
except ImportError:
    pydantic = None


class ErrprintCalled(Exception):
    """Exception raised instead of `errprint` function outputting to stderr"""
    pass


def patched_errprint(*args, **kwargs):
    output = StringIO()
    print(*args, file=output, **kwargs)
    contents = output.getvalue()
    output.close()
    raise ErrprintCalled(contents)


# put our function instead of the original one (monkeypatching)
l.errprint = patched_errprint


class TestConstDrive(unittest.TestCase):
    def test_const_drive_caller(self):
        """Check that the new module can be used the same way as the current one"""

        # just value
        cdc = l.ConstDriveCaller(const_value=42)
        self.assertEqual(cdc.idx, None)
        self.assertEqual(cdc.const_value, 42)
        self.assertEqual(str(cdc), 'const, 42')

        # index and value
        cdc = l.ConstDriveCaller(idx=1, const_value=42)
        self.assertEqual(cdc.idx, 1)
        self.assertEqual(cdc.const_value, 42)
        self.assertEqual(str(cdc), 'drive caller: 1, const, 42')

        # can't use positional arguments, arguably better
        with self.assertRaises(TypeError):
            cdc = l.ConstDriveCaller(42, 1)
            self.assertEqual(cdc.idx, 1)
            self.assertEqual(cdc.const_value, 42)

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_missing_arguments(self):
        with self.assertRaises(Exception):
            l.ConstDriveCaller()
        with self.assertRaises(Exception):
            l.ConstDriveCaller(idx=1)

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_wrong_argument_types(self):
        with self.assertRaises(Exception):
            l.ConstDriveCaller(idx=1.0)

        with self.assertRaises(Exception):
            l.ConstDriveCaller(const_value='a')

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_extra_arguments(self):
        with self.assertRaises(Exception):
            l.ConstDriveCaller(const_value=42, foo=1.0)
        # allows to catch typos in optional arguments
        with self.assertRaises(Exception):
            l.ConstDriveCaller(const_value=42, ibx=1)
        # that also prevents wrongly assigning other members in constructor
        with self.assertRaises(Exception):
            l.ConstDriveCaller(const_value=42, drive_type='bar')

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_schema(self):
        pydantic.TypeAdapter(l.ConstDriveCaller).json_schema()

    def test_abstract_class(self):
        """Check that user can't create abstract classes, which are used only to share functionality (can't be part of MBDyn output)"""
        with self.assertRaises(TypeError):
            e = l.MBEntity()
        with self.assertRaises(TypeError):
            dc = l.DriveCaller2()


if __name__ == '__main__':
    unittest.main()