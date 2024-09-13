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
        self.scalar_law = l.LinearElastic(law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW, stiffness=1e9)
        self.vector_3d_law = l.LinearElastic(law_type=l.ConstitutiveLaw.LawType.D3_ISOTROPIC_LAW, stiffness=1e9)
        self.vector_6d_law = l.LinearElastic(law_type=l.ConstitutiveLaw.LawType.D6_ISOTROPIC_LAW, stiffness=1e9)

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
        small_stiffness = l.LinearElastic(law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW, stiffness=1e-9)
        large_stiffness = l.LinearElastic(law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW, stiffness=1e12)
        zero_stiffness = l.LinearElastic(law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW, stiffness=0)
        self.assertEqual(small_stiffness.stiffness, 1e-9)
        self.assertEqual(large_stiffness.stiffness, 1e12)
        self.assertEqual(zero_stiffness.stiffness, 0)

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_missing_arguments(self):
        with self.assertRaises(Exception):
            l.LinearElastic(law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW)
        with self.assertRaises(Exception):
            l.LinearElastic(stiffness=1e9)

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_invalid_stiffness_type(self):
        with self.assertRaises(Exception):
            l.LinearElastic(law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW, stiffness="invalid")
        with self.assertRaises(Exception):
            l.LinearElastic(law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW, stiffness=None)

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_extra_arguments(self):
        with self.assertRaises(Exception):
            l.LinearElastic(law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW, stiffness=1e9, foo=1.0)

    def test_str_with_different_stiffness(self):
        small_stiffness = l.LinearElastic(law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW, stiffness=1e-9)
        large_stiffness = l.LinearElastic(law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW, stiffness=1e12)
        zero_stiffness = l.LinearElastic(law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW, stiffness=0)
        self.assertEqual(str(small_stiffness), f'{small_stiffness.const_law_header()}, 1e-09')
        self.assertEqual(str(large_stiffness), f'{large_stiffness.const_law_header()}, 1000000000000.0')
        self.assertEqual(str(zero_stiffness), f'{zero_stiffness.const_law_header()}, 0.0')

class TestLinearViscousGeneric(unittest.TestCase):
    def setUp(self):
        self.scalar_law = l.LinearViscousGeneric(law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW, viscosity=1e9)
        self.vector_3d_law = l.LinearViscousGeneric(law_type=l.ConstitutiveLaw.LawType.D3_ISOTROPIC_LAW, viscosity=[[1e9, 0, 0], [0, 1e9, 0], [0, 0, 1e9]])
        self.vector_6d_law = l.LinearViscousGeneric(law_type=l.ConstitutiveLaw.LawType.D6_ISOTROPIC_LAW, viscosity=[[1e9, 0, 0, 0, 0, 0], [0, 1e9, 0, 0, 0, 0], [0, 0, 1e9, 0, 0, 0], [0, 0, 0, 1e9, 0, 0], [0, 0, 0, 0, 1e9, 0], [0, 0, 0, 0, 0, 1e9]])

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
        small_viscosity = l.LinearViscousGeneric(law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW, viscosity=1e-9)
        large_viscosity = l.LinearViscousGeneric(law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW, viscosity=1e12)
        zero_viscosity = l.LinearViscousGeneric(law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW, viscosity=0)
        self.assertEqual(small_viscosity.viscosity, 1e-9)
        self.assertEqual(large_viscosity.viscosity, 1e12)
        self.assertEqual(zero_viscosity.viscosity, 0)

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_missing_arguments(self):
        with self.assertRaises(Exception):
            l.LinearViscousGeneric(law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW)
        with self.assertRaises(Exception):
            l.LinearViscousGeneric(viscosity=1e9)

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_invalid_viscosity_type(self):
        with self.assertRaises(Exception):
            l.LinearViscousGeneric(law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW, viscosity="invalid")
        with self.assertRaises(Exception):
            l.LinearViscousGeneric(law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW, viscosity=None)

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_extra_arguments(self):
        with self.assertRaises(Exception):
            l.LinearViscousGeneric(law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW, viscosity=1e9, foo=1.0)

    def test_str_with_different_viscosity(self):
        small_viscosity = l.LinearViscousGeneric(law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW, viscosity=1e-9)
        large_viscosity = l.LinearViscousGeneric(law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW, viscosity=1e12)
        zero_viscosity = l.LinearViscousGeneric(law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW, viscosity=0)
        self.assertEqual(str(small_viscosity), f'{small_viscosity.const_law_header()}, 1e-09')
        self.assertEqual(str(large_viscosity), f'{large_viscosity.const_law_header()}, 1000000000000.0')
        self.assertEqual(str(zero_viscosity), f'{zero_viscosity.const_law_header()}, 0.0')

class TestLinearViscoelasticGeneric(unittest.TestCase):
    def test_valid_initialization_with_viscosity(self):
        stiffness = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        viscosity = [[2.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 2.0]]
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
        stiffness = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
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
        stiffness = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        viscosity = [[2.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 2.0]]
        law = l.LinearViscoelasticGeneric(
            law_type=l.ConstitutiveLaw.LawType.D3_ISOTROPIC_LAW,
            stiffness=stiffness,
            viscosity=viscosity
        )
        expected_str = f'{law.const_law_header()},\n\t1.0, 0.0, 0.0,\n\t0.0, 1.0, 0.0,\n\t0.0, 0.0, 1.0,\n\t2.0, 0.0, 0.0,\n\t0.0, 2.0, 0.0,\n\t0.0, 0.0, 2.0'
        self.assertEqual(str(law), expected_str)

    def test_str_representation_with_factor(self):
        stiffness = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        factor = 0.5
        law = l.LinearViscoelasticGeneric(
            law_type=l.ConstitutiveLaw.LawType.D3_ISOTROPIC_LAW,
            stiffness=stiffness,
            factor=factor
        )
        expected_str = f'{law.const_law_header()},\n\t1.0, 0.0, 0.0,\n\t0.0, 1.0, 0.0,\n\t0.0, 0.0, 1.0, proportional, 0.5'
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

class TestPosition2(unittest.TestCase):
    def test_initialization_with_list(self):
        pos = l.Position('', [1.0, 2.0, 3.0])
        self.assertEqual(pos.relative_position, [1.0, 2.0, 3.0])
        pos2 = l.Position2(reference='', relative_position=[1.0, 2.0, 3.0])
        self.assertEqual(pos2.relative_position, [1.0, 2.0, 3.0])
        self.assertEqual(pos.relative_position, pos2.relative_position)

    def test_initialization_with_non_list(self):
        pos = l.Position('', 1.0)
        self.assertEqual(pos.relative_position, [1.0])
        pos2 = l.Position2(reference='', relative_position=1.0)
        self.assertEqual(pos2.relative_position, [1.0])
        self.assertEqual(pos.relative_position, pos2.relative_position)

    def test_string_representation_with_empty_reference(self):
        pos = l.Position('', [1.0, 2.0, 3.0])
        self.assertEqual(str(pos), '1.0, 2.0, 3.0')
        pos2 = l.Position2(reference='', relative_position=[1.0, 2.0, 3.0])
        self.assertEqual(str(pos2), '1.0, 2.0, 3.0')
        self.assertEqual(str(pos), str(pos2))

    def test_string_representation_with_non_empty_reference(self):
        pos = l.Position('global', [1.0, 2.0, 3.0])
        self.assertEqual(str(pos), 'reference, global, 1.0, 2.0, 3.0')
        pos2 = l.Position2(reference='global', relative_position=[1.0, 2.0, 3.0])
        self.assertEqual(str(pos2), 'reference, global, 1.0, 2.0, 3.0')
        self.assertEqual(str(pos), str(pos2))

    def test_isnull(self):
        pos = l.Position('', [ l.null()])
        self.assertTrue(pos.isnull())
        pos2 = l.Position2(reference='', relative_position=[l.null()])
        self.assertTrue(pos2.isnull())
        self.assertEqual(str(pos), str(pos2))

    def test_iseye(self):
        pos = l.Position('', [l.eye()])
        self.assertTrue(pos.iseye())
        pos2 = l.Position2(reference='', relative_position=[l.eye()])
        self.assertTrue(pos2.iseye())
        self.assertEqual(str(pos), str(pos2))

class TestReference2(unittest.TestCase):
    def test_initialization(self):
        pos2 = l.Position2(reference='', relative_position=[1.0, 2.0, 3.0])
        orient2 = l.Position2(reference='', relative_position=[0.0, 0.0, 1.0])
        vel2 = l.Position2(reference='', relative_position=[0.0, 0.0, 0.0])
        angvel2 = l.Position2(reference='', relative_position=[0.1, 0.1, 0.1])
        ref2 = l.Reference2(idx=1, position=pos2, orientation=orient2, velocity=vel2, angular_velocity=angvel2)
        self.assertEqual(str(ref2), 'reference: 1, \n\t1.0, 2.0, 3.0,\n\t0.0, 0.0, 1.0,\n\t0.0, 0.0, 0.0,\n\t0.1, 0.1, 0.1;\n')

    def test_against_Reference(self):
        pos = l.Position('', [1.0, 2.0, 3.0])
        orient = l.Position('', [0.0, 0.0, 1.0])
        vel = l.Position('', [0.0, 0.0, 0.0])
        angvel = l.Position('', [0.1, 0.1, 0.1])
        ref = l.Reference(1, pos, orient, vel, angvel)
        pos2 = l.Position2(reference='', relative_position=[1.0, 2.0, 3.0])
        orient2 = l.Position2(reference='', relative_position=[0.0, 0.0, 1.0])
        vel2 = l.Position2(reference='', relative_position=[0.0, 0.0, 0.0])
        angvel2 = l.Position2(reference='', relative_position=[0.1, 0.1, 0.1])
        ref2 = l.Reference2(idx=1, position=pos2, orientation=orient2, velocity=vel2, angular_velocity=angvel2)
        self.assertEqual(str(ref), str(ref2))

class TestCardanoPin(unittest.TestCase):

    def test_abstract_class(self):
        """Check that user can't create abstract classes, which are used only to share functionality (can't be part of MBDyn output)"""
        with self.assertRaises(TypeError):
            e = l.Element2()

    def setUp(self):
        self.node_label = 5
        self.relative_position = [0.0, 1.0, 2.0]
        self.absolute_pin_position = l.Position2(reference='global', relative_position=[3.0, 4.0, 5.0])

        # Optional values for testing with orientations
        self.relative_orientation_matrix = l.Position2(
            relative_position=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            reference=''
        )
        self.absolute_orientation_matrix = l.Position2(
            relative_position=[[0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
            reference='node'
        )

        # Initialize CardanoPin with required fields
        self.cardano_pin = l.CardanoPin(
            idx=1,
            output='yes',
            node_label=self.node_label,
            position=l.Position2(relative_position=self.relative_position, reference='global'),
            absolute_pin_position=self.absolute_pin_position
        )

    def test_initialization(self):
        # Test that the CardanoPin initializes correctly with provided values
        self.assertEqual(self.cardano_pin.node_label, self.node_label)
        self.assertIsInstance(self.cardano_pin.position, l.Position2)
        self.assertEqual(self.cardano_pin.position.relative_position, self.relative_position)
        self.assertEqual(self.cardano_pin.position.reference, 'global')
        self.assertEqual(self.cardano_pin.absolute_pin_position, self.absolute_pin_position)
        self.assertIsNone(self.cardano_pin.orientation_mat)
        self.assertIsNone(self.cardano_pin.absolute_pin_orientation_mat)
        self.assertEqual(self.cardano_pin.idx, 1)
        self.assertEqual(self.cardano_pin.output, 'yes')

    def test_str_representation_without_optional(self):
        # Test the string output when optional orientation matrices are not provided
        expected_str = (
            f'{self.cardano_pin.element_header()}, cardano pin,\n\t{self.node_label},'
            f'\n\t\tposition, {self.cardano_pin.position},'
            f'\n\tposition, {self.cardano_pin.absolute_pin_position}'
            f'{self.cardano_pin.element_footer()}'
        )
        self.assertEqual(str(self.cardano_pin), expected_str)

    def test_str_representation_with_optional(self):
        # Initialize with optional orientation matrices
        cardano_pin_with_orientation = l.CardanoPin(
            idx=2,
            output='no',
            node_label=self.node_label,
            position=l.Position2(relative_position=self.relative_position, reference='global'),
            orientation_mat=self.relative_orientation_matrix,
            absolute_pin_position=self.absolute_pin_position,
            absolute_pin_orientation_mat=self.absolute_orientation_matrix
        )

        expected_str = (
            f'{cardano_pin_with_orientation.element_header()}, cardano pin,\n\t{self.node_label},'
            f'\n\t\tposition, {cardano_pin_with_orientation.position},'
            f'\n\t\torientation, {self.relative_orientation_matrix},'
            f'\n\tposition, {cardano_pin_with_orientation.absolute_pin_position},'
            f'\n\torientation, {self.absolute_orientation_matrix}'
            f'{cardano_pin_with_orientation.element_footer()}'
        )
        self.assertEqual(str(cardano_pin_with_orientation), expected_str)

    def test_optional_none_handling(self):
        # Test to check that None is handled correctly for optional orientation matrices
        cardano_pin_without_orientation = l.CardanoPin(
            idx=3,
            node_label=self.node_label,
            position=l.Position2(relative_position=self.relative_position, reference=''),
            absolute_pin_position=self.absolute_pin_position
        )

        # Assert that orientation matrices remain None
        self.assertIsNone(cardano_pin_without_orientation.orientation_mat)
        self.assertIsNone(cardano_pin_without_orientation.absolute_pin_orientation_mat)

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_invalid_node_label(self):
        # Test that passing invalid node_label raises the appropriate error
        with self.assertRaises(Exception):
            l.CardanoPin(
                idx=4,
                node_label="invalid_label",  # Invalid type for node_label
                position=l.Position2(relative_position=self.relative_position, reference='global'),
                absolute_pin_position=self.absolute_pin_position
            )

    def test_invalid_position(self):
        # Test invalid Position2 for position and absolute_pin_position
        with self.assertRaises(ValueError):
            l.CardanoPin(
                idx=5,
                node_label=self.node_label,
                position=l.Position2(relative_position='invalid_value', reference='global'),
                absolute_pin_position=self.absolute_pin_position
            )

    def test_isnull_function(self):
        # Test if the `isnull()` function works correctly in Position2
        null_position = l.Position2(relative_position=[l.null()], reference='')
        self.assertTrue(null_position.isnull())

    def test_iseye_function(self):
        # Test if the `iseye()` function works correctly in Position2
        eye_position = l.Position2(relative_position=[l.eye()], reference='')
        self.assertTrue(eye_position.iseye())

class TestCardanoRotation(unittest.TestCase):

    def setUp(self):
        self.node_1_label = 1
        self.node_2_label = 2

        # Optional values for testing with orientations
        self.orientation_matrix_1 = l.Position2(
            relative_position=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            reference=''
        )
        self.orientation_matrix_2 = l.Position2(
            relative_position=[[0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
            reference='node'
        )

        # Initialize CardanoRotation with required fields
        self.cardano_rotation = l.CardanoRotation(
            idx=1,
            node_1_label=self.node_1_label,
            node_2_label=self.node_2_label
        )

    def test_initialization(self):
        # Test that the CardanoRotation initializes correctly with provided values
        self.assertEqual(self.cardano_rotation.node_1_label, self.node_1_label)
        self.assertEqual(self.cardano_rotation.node_2_label, self.node_2_label)
        self.assertIsNone(self.cardano_rotation.orientation_mat_1)
        self.assertIsNone(self.cardano_rotation.orientation_mat_2)
        self.assertEqual(self.cardano_rotation.idx, 1)
        self.assertEqual(self.cardano_rotation.output, 'yes')

    def test_str_representation_without_optional(self):
        # Test the string output when optional orientation matrices are not provided
        expected_str = (
            f'{self.cardano_rotation.element_header()}, cardano rotation,\n\t{self.node_1_label},'
            f'\n\t{self.node_2_label}'
            f'{self.cardano_rotation.element_footer()}'
        )
        self.assertEqual(str(self.cardano_rotation), expected_str)

    def test_str_representation_with_optional(self):
        # Initialize with optional orientation matrices
        cardano_rotation_with_orientation = l.CardanoRotation(
            idx=2,
            output='no',
            node_1_label=self.node_1_label,
            orientation_mat_1=self.orientation_matrix_1,
            node_2_label=self.node_2_label,
            orientation_mat_2=self.orientation_matrix_2
        )

        expected_str = (
            f'{cardano_rotation_with_orientation.element_header()}, cardano rotation,\n\t{self.node_1_label},'
            f'\n\t\torientation, {self.orientation_matrix_1},'
            f'\n\t{self.node_2_label},'
            f'\n\t\torientation, {self.orientation_matrix_2}'
            f'{cardano_rotation_with_orientation.element_footer()}'
        )
        self.assertEqual(str(cardano_rotation_with_orientation), expected_str)

    def test_optional_none_handling(self):
        # Test to check that None is handled correctly for optional orientation matrices
        cardano_rotation_without_orientation = l.CardanoRotation(
            idx=3,
            node_1_label=self.node_1_label,
            node_2_label=self.node_2_label
        )

        # Assert that orientation matrices remain None
        self.assertIsNone(cardano_rotation_without_orientation.orientation_mat_1)
        self.assertIsNone(cardano_rotation_without_orientation.orientation_mat_2)

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_invalid_node_labels(self):
        # Test that passing invalid node labels raises the appropriate error
        with self.assertRaises(Exception):
            l.CardanoRotation(
                idx=4,
                node_1_label="invalid_label",  # Invalid type for node_1_label
                node_2_label=self.node_2_label
            )

        with self.assertRaises(Exception):
            l.CardanoRotation(
                idx=5,
                node_1_label=self.node_1_label,
                node_2_label="invalid_label"  # Invalid type for node_2_label
            )
        
if __name__ == '__main__':
    unittest.main()
