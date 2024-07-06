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

class TestLinearElastic(unittest.TestCase):
    def setUp(self):
        self.scalar_law = l.LinearElastic(law_type="scalar isotropic law", stiffness=1e9)
        self.vector_3d_law = l.LinearElastic(law_type="3D isotropic law", stiffness=1e9)
        self.vector_6d_law = l.LinearElastic(law_type="6D isotropic law", stiffness=1e9)

    def test_name(self):
        self.assertEqual(self.scalar_law.law_type, l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW)
        self.assertEqual(self.vector_3d_law.law_type, l.ConstitutiveLaw.LawType.D3_ISOTROPIC_LAW)
        self.assertEqual(self.vector_6d_law.law_type, l.ConstitutiveLaw.LawType.D6_ISOTROPIC_LAW)
        
    def test_const_law_name(self):
        self.assertEqual(self.scalar_law.const_law_header(), 'linear elastic')
        self.assertEqual(self.vector_3d_law.const_law_header(), 'linear elastic isotropic')
        self.assertEqual(self.vector_6d_law.const_law_header(), 'linear elastic isotropic')

    def test_str(self):
        self.assertEqual(str(self.scalar_law), f'{self.scalar_law.const_law_header()}, 1000000000.0')
        self.assertEqual(str(self.vector_3d_law), f'{self.vector_3d_law.const_law_header()}, 1000000000.0')
        self.assertEqual(str(self.vector_6d_law), f'{self.vector_6d_law.const_law_header()}, 1000000000.0')

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_invalid_law_type(self):
        with self.assertRaises(Exception):
            l.LinearElastic(law_type='INVALID_LAW_TYPE', stiffness=1e9)

    def test_different_stiffness_values(self):
        small_stiffness = l.LinearElastic(law_type="scalar isotropic law", stiffness=1e-9)
        large_stiffness = l.LinearElastic(law_type="scalar isotropic law", stiffness=1e12)
        zero_stiffness = l.LinearElastic(law_type="scalar isotropic law", stiffness=0)
        self.assertEqual(small_stiffness.stiffness, 1e-9)
        self.assertEqual(large_stiffness.stiffness, 1e12)
        self.assertEqual(zero_stiffness.stiffness, 0)

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_missing_arguments(self):
        with self.assertRaises(Exception):
            l.LinearElastic(law_type="scalar isotropic law")
        with self.assertRaises(Exception):
            l.LinearElastic(stiffness=1e9)

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_invalid_stiffness_type(self):
        with self.assertRaises(Exception):
            l.LinearElastic(law_type="scalar isotropic law", stiffness="invalid")
        with self.assertRaises(Exception):
            l.LinearElastic(law_type="scalar isotropic law", stiffness=None)

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_extra_arguments(self):
        with self.assertRaises(Exception):
            l.LinearElastic(law_type="scalar isotropic law", stiffness=1e9, foo=1.0)

    def test_str_with_different_stiffness(self):
        small_stiffness = l.LinearElastic(law_type="scalar isotropic law", stiffness=1e-9)
        large_stiffness = l.LinearElastic(law_type="scalar isotropic law", stiffness=1e12)
        zero_stiffness = l.LinearElastic(law_type="scalar isotropic law", stiffness=0)
        self.assertEqual(str(small_stiffness), f'{small_stiffness.const_law_header()}, 1e-09')
        self.assertEqual(str(large_stiffness), f'{large_stiffness.const_law_header()}, 1000000000000.0')
        self.assertEqual(str(zero_stiffness), f'{zero_stiffness.const_law_header()}, 0.0')

class TestLinearViscousGeneric(unittest.TestCase):
    def setUp(self):
        self.scalar_law = l.LinearViscousGeneric(law_type="scalar isotropic law", viscosity=1e9)
        self.vector_3d_law = l.LinearViscousGeneric(law_type="3D isotropic law", viscosity=[[1e9, 0, 0], [0, 1e9, 0], [0, 0, 1e9]])
        self.vector_6d_law = l.LinearViscousGeneric(law_type="6D isotropic law", viscosity=[[1e9, 0, 0, 0, 0, 0], [0, 1e9, 0, 0, 0, 0], [0, 0, 1e9, 0, 0, 0], [0, 0, 0, 1e9, 0, 0], [0, 0, 0, 0, 1e9, 0], [0, 0, 0, 0, 0, 1e9]])

    def test_name(self):
        self.assertEqual(self.scalar_law.law_type, l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW)
        self.assertEqual(self.vector_3d_law.law_type, l.ConstitutiveLaw.LawType.D3_ISOTROPIC_LAW)
        self.assertEqual(self.vector_6d_law.law_type, l.ConstitutiveLaw.LawType.D6_ISOTROPIC_LAW)
        
    def test_const_law_name(self):
        self.assertEqual(self.scalar_law.const_law_name(), 'linear viscous generic')
        self.assertEqual(self.vector_3d_law.const_law_name(), 'linear viscous generic')
        self.assertEqual(self.vector_6d_law.const_law_name(), 'linear viscous generic')

    def test_str(self):
        self.assertEqual(str(self.scalar_law), f'{self.scalar_law.const_law_header()}, 1000000000.0')
        self.assertEqual(str(self.vector_3d_law), f'{self.vector_3d_law.const_law_header()},\n\t1000000000.0, 0.0, 0.0,\n\t0.0, 1000000000.0, 0.0,\n\t0.0, 0.0, 1000000000.0')
        self.assertEqual(str(self.vector_6d_law), f'{self.vector_6d_law.const_law_header()},\n\t1000000000.0, 0.0, 0.0, 0.0, 0.0, 0.0,\n\t0.0, 1000000000.0, 0.0, 0.0, 0.0, 0.0,\n\t0.0, 0.0, 1000000000.0, 0.0, 0.0, 0.0,\n\t0.0, 0.0, 0.0, 1000000000.0, 0.0, 0.0,\n\t0.0, 0.0, 0.0, 0.0, 1000000000.0, 0.0,\n\t0.0, 0.0, 0.0, 0.0, 0.0, 1000000000.0')

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_invalid_law_type(self):
        with self.assertRaises(Exception):
            l.LinearViscousGeneric(law_type='INVALID_LAW_TYPE', viscosity=1e9)

    def test_different_viscosity_values(self):
        small_viscosity = l.LinearViscousGeneric(law_type="scalar isotropic law", viscosity=1e-9)
        large_viscosity = l.LinearViscousGeneric(law_type="scalar isotropic law", viscosity=1e12)
        zero_viscosity = l.LinearViscousGeneric(law_type="scalar isotropic law", viscosity=0)
        self.assertEqual(small_viscosity.viscosity, 1e-9)
        self.assertEqual(large_viscosity.viscosity, 1e12)
        self.assertEqual(zero_viscosity.viscosity, 0)

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_missing_arguments(self):
        with self.assertRaises(Exception):
            l.LinearViscousGeneric(law_type="scalar isotropic law")
        with self.assertRaises(Exception):
            l.LinearViscousGeneric(viscosity=1e9)

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_invalid_viscosity_type(self):
        with self.assertRaises(Exception):
            l.LinearViscousGeneric(law_type="scalar isotropic law", viscosity="invalid")
        with self.assertRaises(Exception):
            l.LinearViscousGeneric(law_type="scalar isotropic law", viscosity=None)

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_extra_arguments(self):
        with self.assertRaises(Exception):
            l.LinearViscousGeneric(law_type="scalar isotropic law", viscosity=1e9, foo=1.0)

    def test_str_with_different_viscosity(self):
        small_viscosity = l.LinearViscousGeneric(law_type="scalar isotropic law", viscosity=1e-9)
        large_viscosity = l.LinearViscousGeneric(law_type="scalar isotropic law", viscosity=1e12)
        zero_viscosity = l.LinearViscousGeneric(law_type="scalar isotropic law", viscosity=0)
        self.assertEqual(str(small_viscosity), f'{small_viscosity.const_law_header()}, 1e-09')
        self.assertEqual(str(large_viscosity), f'{large_viscosity.const_law_header()}, 1000000000000.0')
        self.assertEqual(str(zero_viscosity), f'{zero_viscosity.const_law_header()}, 0.0')

class TestLinearViscoelasticGeneric(unittest.TestCase):

    def test_valid_initialization_with_viscosity(self):
        stiffness = [[1.0, 0.0], [0.0, 1.0]]
        viscosity = [[2.0, 0.0], [0.0, 2.0]]

        law = l.LinearViscoelasticGeneric(
            law_type=l.ConstitutiveLaw.LawType.D3_ISOTROPIC_LAW,
            stiffness=stiffness,
            viscosity=viscosity
        )

        self.assertEqual(law.const_law_name(), 'linear viscoelastic generic')
        self.assertEqual(law.stiffness, stiffness)
        self.assertEqual(law.viscosity, viscosity)
        self.assertIsNone(law.factor)

    def test_valid_initialization_with_factor(self):
        stiffness = [[1.0, 0.0], [0.0, 1.0]]
        factor = 0.5

        law = l.LinearViscoelasticGeneric(
            law_type=l.ConstitutiveLaw.LawType.D3_ISOTROPIC_LAW,
            stiffness=stiffness,
            factor=factor
        )

        self.assertEqual(law.const_law_name(), 'linear viscoelastic generic')
        self.assertEqual(law.stiffness, stiffness)
        self.assertEqual(law.factor, factor)
        self.assertIsNone(law.viscosity)

    def test_str_representation_with_viscosity(self):
        stiffness = [[1.0, 0.0], [0.0, 1.0]]
        viscosity = [[2.0, 0.0], [0.0, 2.0]]

        law = l.LinearViscoelasticGeneric(
            law_type=l.ConstitutiveLaw.LawType.D3_ISOTROPIC_LAW,
            stiffness=stiffness,
            viscosity=viscosity
        )

        expected_str = f'{law.const_law_header()},\n\t1.0, 0.0,\n\t0.0, 1.0,\n2.0, 0.0,\n0.0, 2.0'
        self.assertEqual(str(law), expected_str)

    def test_str_representation_with_factor(self):
        stiffness = [[1.0, 0.0], [0.0, 1.0]]
        factor = 0.5

        law = l.LinearViscoelasticGeneric(
            law_type=l.ConstitutiveLaw.LawType.D3_ISOTROPIC_LAW,
            stiffness=stiffness,
            factor=factor
        )

        expected_str = f'{law.const_law_header()},\n\t1.0, 0.0,\n\t0.0, 1.0, proportional, 0.5'
        self.assertEqual(str(law), expected_str)

    def test_invalid_stiffness_matrix(self):
        with self.assertRaises(ValueError):
            invalid_stiffness = [[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]]
            l.LinearViscoelasticGeneric(
                law_type=l.ConstitutiveLaw.LawType.D3_ISOTROPIC_LAW,
                stiffness=invalid_stiffness,
                factor=0.5
            )

    def test_invalid_viscosity_matrix(self):
        with self.assertRaises(ValueError):
            invalid_viscosity = [[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]]
            l.LinearViscoelasticGeneric(
                law_type=l.ConstitutiveLaw.LawType.D3_ISOTROPIC_LAW,
                stiffness=[[1.0]],
                viscosity=invalid_viscosity
            )

    def test_missing_factor_or_viscosity(self):
        with self.assertRaises(ValueError):
            l.LinearViscoelasticGeneric(
                law_type=l.ConstitutiveLaw.LawType.D3_ISOTROPIC_LAW,
                stiffness=[[1.0]]
            )

    def test_both_viscosity_and_factor_provided(self):
        with self.assertRaises(ValueError):
            l.LinearViscoelasticGeneric(
                law_type=l.ConstitutiveLaw.LawType.D3_ISOTROPIC_LAW,
                stiffness=[[1.0]],
                viscosity=[[2.0]],
                factor=0.5
            )

if __name__ == '__main__':
    unittest.main()