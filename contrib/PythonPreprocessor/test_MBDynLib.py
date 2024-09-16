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

class TestAngularAcceleration(unittest.TestCase):

    def test_valid_input(self):
        """Test that AngularAcceleration works with valid input"""
        # Valid instance of ConstDriveCaller
        const_drive = l.ConstDriveCaller(const_value=5.0)
        
        # Create an AngularAcceleration instance with valid inputs
        angular_accel = l.AngularAcceleration(
            idx=1,
            node_label=1,
            relative_direction=[1, 0, 0],
            acceleration=const_drive
        )
        
        expected_output = '''joint: 1, angular acceleration,\n\t1, [1, 0, 0],\n\tconst, 5.0;\n'''
        self.assertEqual(str(angular_accel), expected_output)

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_invalid_relative_direction_length(self):
        """Test that AngularAcceleration raises an error for invalid relative_direction length"""
        const_drive = l.ConstDriveCaller(const_value=5.0)

        # relative_direction must have exactly 3 elements, expect failure
        with self.assertRaises(Exception):
            l.AngularAcceleration(
                idx=1,
                node_label=1,
                relative_direction=[1, 0],  # Invalid length
                acceleration=const_drive
            )

    def test_invalid_relative_direction_magnitude(self):
        """Test that AngularAcceleration raises an error for non-unit vector relative_direction"""
        const_drive = l.ConstDriveCaller(const_value=5.0)

        # relative_direction must be a unit vector (magnitude = 1), expect failure
        with self.assertRaises(ValueError):
            l.AngularAcceleration(
                idx=1,
                node_label=1,
                relative_direction=[2, 0, 0],  # Invalid magnitude (not a unit vector)
                acceleration=const_drive
            )

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_invalid_acceleration_type(self):
        """Test that AngularAcceleration raises an error for invalid acceleration type"""
        # Pass an invalid type for acceleration
        with self.assertRaises(Exception):
            l.AngularAcceleration(
                idx=1,
                node_label=1,
                relative_direction=[1, 0, 0],
                acceleration=5  # Invalid type, should be DriveCaller or its subclass
            )

    def test_optional_output(self):
        """Test that the 'output' field is optional and defaults to 'yes'"""
        const_drive = l.ConstDriveCaller(const_value=5.0)

        # Create AngularAcceleration without specifying output
        angular_accel = l.AngularAcceleration(
            idx=1,
            node_label=1,
            relative_direction=[1, 0, 0],
            acceleration=const_drive
        )
        
        expected_output = '''joint: 1, angular acceleration,\n\t1, [1, 0, 0],\n\tconst, 5.0;\n'''
        self.assertEqual(str(angular_accel), expected_output)

    def test_custom_output(self):
        """Test that the 'output' field is properly set when customized"""
        const_drive = l.ConstDriveCaller(const_value=5.0)

        # Create AngularAcceleration with custom output
        angular_accel = l.AngularAcceleration(
            idx=1,
            node_label=1,
            relative_direction=[1, 0, 0],
            acceleration=const_drive,
            output='no'
        )
        
        expected_output = '''joint: 1, angular acceleration,\n\t1, [1, 0, 0],\n\tconst, 5.0,\n\toutput, no;\n'''
        self.assertEqual(str(angular_accel), expected_output)

class TestAngularVelocity(unittest.TestCase):

    def test_valid_input(self):
        """Test that AngularVelocity works with valid input"""
        # Valid instance of ConstDriveCaller
        const_drive = l.ConstDriveCaller(const_value=5.0)
        
        # Create an AngularVelocity instance with valid inputs
        angular_vel = l.AngularVelocity(
            idx=1,
            node_label=1,
            relative_direction=[1, 0, 0],
            velocity=const_drive
        )
        
        expected_output = '''joint: 1, angular velocity,\n\t1, [1, 0, 0],\n\tconst, 5.0;\n'''
        self.assertEqual(str(angular_vel), expected_output)

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_invalid_relative_direction_length(self):
        """Test that AngularVelocity raises an error for invalid relative_direction length"""
        const_drive = l.ConstDriveCaller(const_value=5.0)

        # relative_direction must have exactly 3 elements, expect failure
        with self.assertRaises(Exception):
            l.AngularVelocity(
                idx=1,
                node_label=1,
                relative_direction=[1, 0],  # Invalid length
                velocity=const_drive
            )

    def test_invalid_relative_direction_magnitude(self):
        """Test that AngularVelocity raises an error for non-unit vector relative_direction"""
        const_drive = l.ConstDriveCaller(const_value=5.0)

        # relative_direction must be a unit vector (magnitude = 1), expect failure
        with self.assertRaises(ValueError):
            l.AngularVelocity(
                idx=1,
                node_label=1,
                relative_direction=[2, 0, 0],  # Invalid magnitude (not a unit vector)
                velocity=const_drive
            )

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_invalid_velocity_type(self):
        """Test that AngularVelocity raises an error for invalid velocity type"""
        # Pass an invalid type for velocity
        with self.assertRaises(Exception):
            l.AngularVelocity(
                idx=1,
                node_label=1,
                relative_direction=[1, 0, 0],
                velocity=5  # Invalid type, should be DriveCaller or its subclass
            )

    def test_optional_output(self):
        """Test that the 'output' field is optional and defaults to 'yes'"""
        const_drive = l.ConstDriveCaller(const_value=5.0)

        # Create AngularVelocity without specifying output
        angular_vel = l.AngularVelocity(
            idx=1,
            node_label=1,
            relative_direction=[1, 0, 0],
            velocity=const_drive
        )
        
        expected_output = '''joint: 1, angular velocity,\n\t1, [1, 0, 0],\n\tconst, 5.0;\n'''
        self.assertEqual(str(angular_vel), expected_output)

    def test_custom_output(self):
        """Test that the 'output' field is properly set when customized"""
        const_drive = l.ConstDriveCaller(const_value=5.0)

        # Create AngularVelocity with custom output
        angular_vel = l.AngularVelocity(
            idx=1,
            node_label=1,
            relative_direction=[1, 0, 0],
            velocity=const_drive,
            output='no'
        )
        
        expected_output = '''joint: 1, angular velocity,\n\t1, [1, 0, 0],\n\tconst, 5.0,\n\toutput, no;\n'''
        self.assertEqual(str(angular_vel), expected_output)

class TestAxialRotation(unittest.TestCase):

    def test_valid_input(self):
        """Test that AxialRotation works with valid input"""
        # Valid instances of Position2 and DriveCaller
        position1 = l.Position2(reference='global', relative_position=[0, 0, 0])
        orientation1 = l.Position2(reference='global', relative_position=[1, 0, 0])
        position2 = l.Position2(reference='global', relative_position=[1, 1, 1])
        orientation2 = l.Position2(reference='global', relative_position=[0, 1, 0])
        drive_caller = l.ConstDriveCaller(const_value=5.0)
        
        # Create an AxialRotation instance with valid inputs
        axial_rot = l.AxialRotation(
            idx=1,
            node_1_label=1,
            position_1=position1,
            orientation_mat_1=orientation1,
            node_2_label=2,
            position_2=position2,
            orientation_mat_2=orientation2,
            angular_velocity=drive_caller
        )
        
        expected_output = (
            f"{axial_rot.element_header()}, axial rotation,\n"
            f"\t{axial_rot.node_1_label},\n"
            f"\t\tposition, {axial_rot.position_1},\n"
            f"\t\torientation, {axial_rot.orientation_mat_1},\n"
            f"\t{axial_rot.node_2_label},\n"
            f"\t\tposition, {axial_rot.position_2},\n"
            f"\t\torientation, {axial_rot.orientation_mat_2},\n"
            f"\t{axial_rot.angular_velocity}"
            f"{axial_rot.element_footer()}"
        )
        self.maxDiff=None
        self.assertEqual(str(axial_rot), expected_output)

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_invalid_position_type(self):
        """Test that AxialRotation raises an error for invalid position type"""
        # Valid instances of Position2 and DriveCaller
        orientation1 = l.Position2(reference='global', relative_position=[1, 0, 0])
        position2 = l.Position2(reference='global', relative_position=[1, 1, 1])
        orientation2 = l.Position2(reference='global', relative_position=[0, 1, 0])
        drive_caller = l.ConstDriveCaller(const_value=5.0)

        # position_1 must be of type Position2
        with self.assertRaises(Exception):
            l.AxialRotation(
                idx=1,
                node_1_label=1,
                position_1='invalid_position',  # Invalid type
                orientation_mat_1=orientation1,
                node_2_label=2,
                position_2=position2,
                orientation_mat_2=orientation2,
                angular_velocity=drive_caller
            )

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_invalid_orientation_type(self):
        """Test that AxialRotation raises an error for invalid orientation type"""
        # Valid instances of Position2 and DriveCaller
        position1 = l.Position2(reference='global', relative_position=[0, 0, 0])
        position2 = l.Position2(reference='global', relative_position=[1, 1, 1])
        drive_caller = l.ConstDriveCaller(const_value=5.0)

        # orientation_mat_1 must be of type Position2
        with self.assertRaises(Exception):
            l.AxialRotation(
                idx=1,
                node_1_label=1,
                position_1=position1,
                orientation_mat_1='invalid_orientation',  # Invalid type
                node_2_label=2,
                position_2=position2,
                orientation_mat_2=l.Position2(reference='global', relative_position=[0, 1, 0]),
                angular_velocity=drive_caller
            )

    @unittest.skipIf(pydantic is None, "depends on library, since it doesn't prevent correct models from running")
    def test_invalid_angular_velocity_type(self):
        """Test that AxialRotation raises an error for invalid angular_velocity type"""
        # Valid instances of Position2
        position1 = l.Position2(reference='global', relative_position=[0, 0, 0])
        orientation1 = l.Position2(reference='global', relative_position=[1, 0, 0])
        position2 = l.Position2(reference='global', relative_position=[1, 1, 1])
        orientation2 = l.Position2(reference='global', relative_position=[0, 1, 0])

        # angular_velocity must be of type DriveCaller or DriveCaller2
        with self.assertRaises(Exception):
            l.AxialRotation(
                idx=1,
                node_1_label=1,
                position_1=position1,
                orientation_mat_1=orientation1,
                node_2_label=2,
                position_2=position2,
                orientation_mat_2=orientation2,
                angular_velocity='invalid_velocity'  # Invalid type
            )

    def test_optional_output(self):
        """Test that the 'output' field is optional and defaults to 'yes'"""
        # Valid instances of Position2 and DriveCaller
        position1 = l.Position2(reference='global', relative_position=[0, 0, 0])
        orientation1 = l.Position2(reference='global', relative_position=[1, 0, 0])
        position2 = l.Position2(reference='global', relative_position=[1, 1, 1])
        orientation2 = l.Position2(reference='global', relative_position=[0, 1, 0])
        drive_caller = l.ConstDriveCaller(const_value=5.0)

        # Create AxialRotation without specifying output
        axial_rot = l.AxialRotation(
            idx=1,
            node_1_label=1,
            position_1=position1,
            orientation_mat_1=orientation1,
            node_2_label=2,
            position_2=position2,
            orientation_mat_2=orientation2,
            angular_velocity=drive_caller
        )
        expected_output = (
            f"{axial_rot.element_header()}, axial rotation,\n"
            f"\t{axial_rot.node_1_label},\n"
            f"\t\tposition, {axial_rot.position_1},\n"
            f"\t\torientation, {axial_rot.orientation_mat_1},\n"
            f"\t{axial_rot.node_2_label},\n"
            f"\t\tposition, {axial_rot.position_2},\n"
            f"\t\torientation, {axial_rot.orientation_mat_2},\n"
            f"\t{axial_rot.angular_velocity}"
            f"{axial_rot.element_footer()}"
        )  
        self.maxDiff=None      
        self.assertEqual(str(axial_rot), expected_output)

    def test_custom_output(self):
        """Test that the 'output' field is properly set when customized"""
        # Valid instances of Position2 and DriveCaller
        position1 = l.Position2(reference='global', relative_position=[0, 0, 0])
        orientation1 = l.Position2(reference='global', relative_position=[1, 0, 0])
        position2 = l.Position2(reference='global', relative_position=[1, 1, 1])
        orientation2 = l.Position2(reference='global', relative_position=[0, 1, 0])
        drive_caller = l.ConstDriveCaller(const_value=5.0)

        # Create AxialRotation with custom output
        axial_rot = l.AxialRotation(
            idx=1,
            node_1_label=1,
            position_1=position1,
            orientation_mat_1=orientation1,
            node_2_label=2,
            position_2=position2,
            orientation_mat_2=orientation2,
            angular_velocity=drive_caller,
            output='no'
        )
        
        expected_output = (
            f"{axial_rot.element_header()}, axial rotation,\n"
            f"\t{axial_rot.node_1_label},\n"
            f"\t\tposition, {axial_rot.position_1},\n"
            f"\t\torientation, {axial_rot.orientation_mat_1},\n"
            f"\t{axial_rot.node_2_label},\n"
            f"\t\tposition, {axial_rot.position_2},\n"
            f"\t\torientation, {axial_rot.orientation_mat_2},\n"
            f"\t{axial_rot.angular_velocity}"
            f"{axial_rot.element_footer()}"
        )  
        self.maxDiff=None
        self.assertEqual(str(axial_rot), expected_output)

class TestBeamSlider(unittest.TestCase):
    def setUp(self):
        # Define Position2 instances
        self.position1 = l.Position2(
            relative_position=[[0.0, 0.0, 0.0]], 
            reference='global'
        )
        self.position2 = l.Position2(
            relative_position=[[1.0, 0.0, 0.0]], 
            reference='node'
        )
        self.position3 = l.Position2(
            relative_position=[[0.0, 1.0, 0.0]], 
            reference='other node'
        )

        # Define Constitutive Laws
        self.elastic_law = l.LinearElastic(
            law_type=l.ConstitutiveLaw.LawType.D3_ISOTROPIC_LAW,
            stiffness=2000.0
        )

        # Define Beams
        self.beam = l.Beam(
            idx=1,
            nodes=[1, 2, 3],
            positions=[self.position1, self.position2, self.position3],
            orientations=[self.position1, self.position2, self.position3],
            const_laws_orientations=[self.position1, self.position2],
            const_laws=[self.elastic_law, self.elastic_law],
        )
    
    def test_valid_input(self):
        beam_slider = l.BeamSlider(
            idx=1,
            slider_node_label=1,
            position=self.position1,
            orientation=self.position2,
            slider_type='classic',
            beam_number=1,
            three_node_beam=self.beam,
            first_node_offset=self.position1,
            first_node_orientation=self.position2,
            mid_node_offset=self.position2,
            mid_node_orientation=self.position3,
            end_node_offset=self.position3,
            end_node_orientation=self.position1,
            initial_beam=self.beam,
            initial_node=None,
            smearing_factor=0.5
        )
        expected_str = (
            f"joint: {beam_slider.idx}, kinematic,\n"
            f"\t{beam_slider.slider_node_label},\n"
            f"\t\t{beam_slider.position},\n"
            f"\t\thinge, {beam_slider.orientation},\n"
            f"\ttype, {beam_slider.slider_type},\n"
            f"\t{beam_slider.beam_number},\n"
            f"\t\t{beam_slider.three_node_beam}"[:-2] + ",\n"  # Remove ';\n' and add ',\n'
            f"\t\t\t{beam_slider.first_node_offset},\n"
            f"\t\thinge, {beam_slider.first_node_orientation},\n"
            f"\t\t\t{beam_slider.mid_node_offset},\n"
            f"\t\thinge, {beam_slider.mid_node_orientation},\n"
            f"\t\t\t{beam_slider.end_node_offset},\n"
            f"\t\thinge, {beam_slider.end_node_orientation},\n"
            f"\tinitial beam, {beam_slider.initial_beam}"[:-2] + ",\n"  # Remove ';\n' and add ',\n'
            f"\tsmearing, {beam_slider.smearing_factor};\n"
        )
        self.maxDiff=None
        self.assertEqual(str(beam_slider), expected_str)
    
    def test_invalid_slider_type(self):
        with self.assertRaises(ValueError):
            l.BeamSlider(
                idx=1,
                slider_node_label=1,
                position=self.position1,
                orientation=self.position2,
                slider_type='invalid_type',
                beam_number=1,
                three_node_beam=self.beam,
                first_node_offset=self.position1,
                first_node_orientation=self.position2,
                mid_node_offset=self.position2,
                mid_node_orientation=self.position3,
                end_node_offset=self.position3,
                end_node_orientation=self.position1,
                initial_beam=self.beam,
                initial_node=None,
                smearing_factor=0.5
            )
    
    def test_optional_fields(self):
        beam_slider = l.BeamSlider(
            idx=1,
            slider_node_label=1,
            position=self.position1,
            orientation=None,
            slider_type=None,
            beam_number=1,
            three_node_beam=self.beam,
            first_node_offset=self.position1,
            first_node_orientation=None,
            mid_node_offset=self.position2,
            mid_node_orientation=None,
            end_node_offset=self.position3,
            end_node_orientation=None,
            initial_beam=None,
            initial_node=None,
            smearing_factor=None
        )
        expected_str = (
            f"{beam_slider.element_header()}, kinematic,\n"
            f"\t{beam_slider.slider_node_label},\n"
            f"\t\t{beam_slider.position},\n"
            f"\t{beam_slider.beam_number},\n"
            f"\t\t{beam_slider.three_node_beam}"[:-2] + ",\n"  # Remove ';\n' and add ',\n'
            f"\t\t\t{beam_slider.first_node_offset},\n"
            f"\t\t\t{beam_slider.mid_node_offset},\n"
            f"\t\t\t{beam_slider.end_node_offset}"
            f"{beam_slider.element_footer()}"
        )
        self.maxDiff = None
        self.assertEqual(str(beam_slider), expected_str)

    def test_invalid_mid_node_offset_type(self):
        with self.assertRaises(ValueError):
            l.BeamSlider(
                idx=1,
                slider_node_label=1,
                position=self.position1,
                orientation=self.position2,
                slider_type='classic',
                beam_number=1,
                three_node_beam=self.beam,
                first_node_offset=self.position1,
                first_node_orientation=self.position2,
                mid_node_offset='invalid_offset',
                mid_node_orientation=self.position3,
                end_node_offset=self.position3,
                end_node_orientation=self.position1,
                initial_beam=self.beam,
                initial_node=None,
                smearing_factor=0.5
            )

    def test_invalid_end_node_offset_type(self):
        with self.assertRaises(ValueError):
            l.BeamSlider(
                idx=1,
                slider_node_label=1,
                position=self.position1,
                orientation=self.position2,
                slider_type='classic',
                beam_number=1,
                three_node_beam=self.beam,
                first_node_offset=self.position1,
                first_node_orientation=self.position2,
                mid_node_offset=self.position2,
                mid_node_orientation=self.position3,
                end_node_offset='invalid_offset',
                end_node_orientation=self.position1,
                initial_beam=self.beam,
                initial_node=None,
                smearing_factor=0.5
            )

    def test_invalid_initial_node_type(self):
        with self.assertRaises(ValueError):
            l.BeamSlider(
                idx=1,
                slider_node_label=1,
                position=self.position1,
                orientation=self.position2,
                slider_type='classic',
                beam_number=1,
                three_node_beam=self.beam,
                first_node_offset=self.position1,
                first_node_orientation=self.position2,
                mid_node_offset=self.position2,
                mid_node_orientation=self.position3,
                end_node_offset=self.position3,
                end_node_orientation=self.position1,
                initial_beam=self.beam,
                initial_node='invalid_node',
                smearing_factor=0.5
            )

class TestBrake(unittest.TestCase):
    def setUp(self):
        self.position1 = l.Position2(relative_position=[[0.0, 0.0, 0.0]], reference='global')
        self.position2 = l.Position2(relative_position=[[1.0, 0.0, 0.0]], reference='node')
        self.normal_force = l.ConstDriveCaller(const_value=1000.0)

    def test_valid_brake(self):
        brake = l.Brake(
            idx=1,
            node_1_label=1,
            position_1=self.position1,
            node_2_label=2,
            position_2=self.position2,
            average_radius=0.5,
            friction_model="modlugre",
            shape_function="tanh",
            normal_force=self.normal_force
        )
        self.assertIsInstance(brake, l.Brake)

    def test_str_representation(self):
        brake = l.Brake(
            idx=1,
            node_1_label=1,
            position_1=self.position1,
            node_2_label=2,
            position_2=self.position2,
            average_radius=0.5,
            friction_model="modlugre",
            shape_function="tanh",
            normal_force=self.normal_force
        )
        expected_str = (
            "joint: 1, brake,\n"
            "\t1, reference, global, [0.0, 0.0, 0.0],\n"
            "\t2, reference, node, [1.0, 0.0, 0.0],\n"
            "\tfriction, 0.5,\n"
            "\t\tmodlugre,\n"
            "\t\ttanh,\n"
            "\tconst, 1000.0;\n"
        )
        self.assertEqual(str(brake), expected_str)

    def test_with_optional_fields(self):
        brake = l.Brake(
            idx=1,
            node_1_label=1,
            position_1=self.position1,
            orientation_mat_1=self.position2,
            node_2_label=2,
            position_2=self.position2,
            orientation_mat_2=self.position1,
            average_radius=0.5,
            preload=100,
            friction_model="modlugre",
            shape_function="tanh",
            normal_force=self.normal_force
        )
        self.assertIsInstance(brake, l.Brake)
        self.assertEqual(brake.preload, 100)

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

class TestDeformableAxial(unittest.TestCase):

    def setUp(self):
        self.node_1_label = 1
        self.node_2_label = 2

        # Optional values for testing with positions and orientations
        self.position_1 = l.Position2(
            relative_position=[1.0, 0.0, 0.0],
            reference=''
        )
        self.orientation_mat_1 = l.Position2(
            relative_position=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            reference='node'
        )
        self.position_2 = l.Position2(
            relative_position=[0.0, 1.0, 0.0],
            reference='global'
        )
        self.orientation_mat_2 = l.Position2(
            relative_position=[[0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
            reference='node'
        )

        # Example constitutive laws
        self.linear_elastic = l.LinearElastic(
            idx=1,
            law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW,
            stiffness=2000
        )
        
        self.linear_elastic_generic = l.LinearElasticGeneric(
            idx=2,
            law_type=l.ConstitutiveLaw.LawType.D3_ISOTROPIC_LAW,
            stiffness=[[1.0, 0.3, 0.0], [0.3, 1.0, 0.0], [0.0, 0.0, 1.0]]
        )
        
        self.named_const_law = l.NamedConstitutiveLaw("example_named_law")
        self.named_const_law2 = l.NamedConstitutiveLaw(["example_named_law", 1000.0])

        # Initialize DeformableAxial with required fields
        self.deformable_axial = l.DeformableAxial(
            idx=1,
            node_1_label=self.node_1_label,
            node_2_label=self.node_2_label,
            const_law=self.linear_elastic
        )

    def test_initialization(self):
        # Test that the DeformableAxial initializes correctly with provided values
        self.assertEqual(self.deformable_axial.node_1_label, self.node_1_label)
        self.assertEqual(self.deformable_axial.node_2_label, self.node_2_label)
        self.assertIsNone(self.deformable_axial.position_1)
        self.assertIsNone(self.deformable_axial.orientation_mat_1)
        self.assertIsNone(self.deformable_axial.position_2)
        self.assertIsNone(self.deformable_axial.orientation_mat_2)
        self.assertEqual(self.deformable_axial.const_law, self.linear_elastic)
        self.assertEqual(self.deformable_axial.idx, 1)
        self.assertEqual(self.deformable_axial.output, 'yes')

    def test_str_representation_without_optional(self):
        # Test the string output when optional positions and orientations are not provided
        expected_str = (
            f'{self.deformable_axial.element_header()}, deformable axial,\n\t{self.node_1_label},'
            f'\n\t{self.node_2_label},'
            f'\n\t{self.linear_elastic}'
            f'{self.deformable_axial.element_footer()}'
        )
        self.assertEqual(str(self.deformable_axial), expected_str)

    def test_str_representation_with_optional(self):
        # Initialize with optional positions and orientations
        deformable_axial_with_optional = l.DeformableAxial(
            idx=2,
            output='no',
            node_1_label=self.node_1_label,
            position_1=self.position_1,
            orientation_mat_1=self.orientation_mat_1,
            node_2_label=self.node_2_label,
            position_2=self.position_2,
            orientation_mat_2=self.orientation_mat_2,
            const_law=self.linear_elastic_generic
        )

        expected_str = (
            f'{deformable_axial_with_optional.element_header()}, deformable axial,\n\t{self.node_1_label},'
            f'\n\t\tposition, {self.position_1},'
            f'\n\t\torientation, {self.orientation_mat_1},'
            f'\n\t{self.node_2_label},'
            f'\n\t\tposition, {self.position_2},'
            f'\n\t\torientation, {self.orientation_mat_2},'
            f'\n\t{self.linear_elastic_generic}'
            f'{deformable_axial_with_optional.element_footer()}'
        )
        self.assertEqual(str(deformable_axial_with_optional), expected_str)

    def test_optional_none_handling(self):
        # Test to check that None is handled correctly for optional positions and orientations
        deformable_axial_without_optional = l.DeformableAxial(
            idx=3,
            node_1_label=self.node_1_label,
            node_2_label=self.node_2_label,
            const_law=self.named_const_law2
        )

        # Assert that optional parameters remain None
        self.assertIsNone(deformable_axial_without_optional.position_1)
        self.assertIsNone(deformable_axial_without_optional.orientation_mat_1)
        self.assertIsNone(deformable_axial_without_optional.position_2)
        self.assertIsNone(deformable_axial_without_optional.orientation_mat_2)

    def test_invalid_node_labels(self):
        # Test that passing invalid node labels raises the appropriate error
        with self.assertRaises(Exception):
            l.DeformableAxial(
                idx=4,
                node_1_label="invalid_label",  # Invalid type for node_1_label
                node_2_label=self.node_2_label,
                const_law=self.linear_elastic
            )

        with self.assertRaises(Exception):
            l.DeformableAxial(
                idx=5,
                node_1_label=self.node_1_label,
                node_2_label="invalid_label",  # Invalid type for node_2_label
                const_law=self.linear_elastic
            )

    def test_invalid_const_law(self):
        # Test that passing an invalid const_law raises the appropriate error
        with self.assertRaises(Exception):
            l.DeformableAxial(
                idx=6,
                node_1_label=self.node_1_label,
                node_2_label=self.node_2_label,
                const_law="invalid_const_law"  # Invalid type for const_law, users have to use NamedConstitutiveLaw for custom Const Laws
            )

    def test_named_constitutive_law(self):
        # Test with NamedConstitutiveLaw
        deformable_axial_with_named_law = l.DeformableAxial(
            idx=7,
            output='yes',
            node_1_label=self.node_1_label,
            node_2_label=self.node_2_label,
            const_law=self.named_const_law
        )

        expected_str = (
            f'{deformable_axial_with_named_law.element_header()}, deformable axial,\n\t{self.node_1_label},'
            f'\n\t{self.node_2_label},'
            f'\n\t{self.named_const_law}'
            f'{deformable_axial_with_named_law.element_footer()}'
        )
        self.assertEqual(str(deformable_axial_with_named_law), expected_str)

    def test_named_constitutive_law2(self):
        # Test with the second NamedConstitutiveLaw instance
        deformable_axial_with_named_law2 = l.DeformableAxial(
            idx=8,
            output='no',
            node_1_label=self.node_1_label,
            node_2_label=self.node_2_label,
            const_law=self.named_const_law2
        )

        expected_str = (
            f'{deformable_axial_with_named_law2.element_header()}, deformable axial,\n\t{self.node_1_label},'
            f'\n\t{self.node_2_label},'
            f'\n\t{self.named_const_law2}'
            f'{deformable_axial_with_named_law2.element_footer()}'
        )
        self.assertEqual(str(deformable_axial_with_named_law2), expected_str)

    def test_warning_for_named_constitutive_law(self):
        # Test if a warning is issued when using a string for constitutive law
        with self.assertWarns(Warning):
            l.DeformableAxial(
                idx=9,
                node_1_label=self.node_1_label,
                node_2_label=self.node_2_label,
                const_law=l.NamedConstitutiveLaw("Some const law")
            )

class TestDeformableHinge2(unittest.TestCase):

    def setUp(self):
        self.node_1_label = 1
        self.node_2_label = 2

        # Optional values for testing with positions and orientations
        self.position_1 = l.Position2(
            relative_position=[1.0, 0.0, 0.0],
            reference=''
        )
        self.orientation_mat_1 = l.Position2(
            relative_position=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            reference='node'
        )
        self.position_2 = l.Position2(
            relative_position=[0.0, 1.0, 0.0],
            reference='global'
        )
        self.orientation_mat_2 = l.Position2(
            relative_position=[[0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
            reference='node'
        )

        # Example constitutive laws
        self.linear_elastic = l.LinearElastic(
            idx=1,
            law_type=l.ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW,
            stiffness=2000
        )
        
        self.named_const_law = l.NamedConstitutiveLaw("example_named_law")

        # Initialize DeformableHinge2 with required fields
        self.deformable_hinge2 = l.DeformableHinge2(
            idx=1,
            node_1_label=self.node_1_label,
            node_2_label=self.node_2_label,
            const_law=self.linear_elastic
        )

    def test_initialization(self):
        # Test that the DeformableHinge2 initializes correctly with provided values
        self.assertEqual(self.deformable_hinge2.node_1_label, self.node_1_label)
        self.assertEqual(self.deformable_hinge2.node_2_label, self.node_2_label)
        self.assertIsNone(self.deformable_hinge2.position_1)
        self.assertIsNone(self.deformable_hinge2.orientation_mat_1)
        self.assertIsNone(self.deformable_hinge2.position_2)
        self.assertIsNone(self.deformable_hinge2.orientation_mat_2)
        self.assertEqual(self.deformable_hinge2.const_law, self.linear_elastic)
        self.assertEqual(self.deformable_hinge2.idx, 1)

    def test_str_representation_without_optional(self):
        # Test the string output when optional positions and orientations are not provided
        expected_str = (
            f'{self.deformable_hinge2.element_header()}, deformable hinge'
            f',\n\t{self.node_1_label},'
            f'\n\t{self.node_2_label},'
            f'\n\t{self.linear_elastic}'
            f'{self.deformable_hinge2.element_footer()}'
        )
        self.assertEqual(str(self.deformable_hinge2), expected_str)

    def test_str_representation_with_optional(self):
        # Initialize with optional positions and orientations
        deformable_hinge2_with_optional = l.DeformableHinge2(
            idx=2,
            node_1_label=self.node_1_label,
            position_1=self.position_1,
            orientation_mat_1=self.orientation_mat_1,
            node_2_label=self.node_2_label,
            position_2=self.position_2,
            orientation_mat_2=self.orientation_mat_2,
            const_law=self.named_const_law
        )

        expected_str = (
            f'{deformable_hinge2_with_optional.element_header()}, deformable hinge'
            f',\n\t{self.node_1_label},'
            f'\n\t\tposition, {self.position_1},'
            f'\n\t\torientation, {self.orientation_mat_1},'
            f'\n\t{self.node_2_label},'
            f'\n\t\tposition, {self.position_2},'
            f'\n\t\torientation, {self.orientation_mat_2},'
            f'\n\t{self.named_const_law}'
            f'{deformable_hinge2_with_optional.element_footer()}'
        )
        self.assertEqual(str(deformable_hinge2_with_optional), expected_str)

    def test_optional_none_handling(self):
        # Test to check that None is handled correctly for optional positions and orientations
        deformable_hinge2_without_optional = l.DeformableHinge2(
            idx=3,
            node_1_label=self.node_1_label,
            node_2_label=self.node_2_label,
            const_law=self.named_const_law
        )

        # Assert that optional parameters remain None
        self.assertIsNone(deformable_hinge2_without_optional.position_1)
        self.assertIsNone(deformable_hinge2_without_optional.orientation_mat_1)
        self.assertIsNone(deformable_hinge2_without_optional.position_2)
        self.assertIsNone(deformable_hinge2_without_optional.orientation_mat_2)

    def test_invalid_node_labels(self):
        # Test that passing invalid node labels raises the appropriate error
        with self.assertRaises(Exception):
            l.DeformableHinge2(
                idx=4,
                node_1_label="invalid_label",  # Invalid type for node_1_label
                node_2_label=self.node_2_label,
                const_law=self.linear_elastic
            )

        with self.assertRaises(Exception):
            l.DeformableHinge2(
                idx=5,
                node_1_label=self.node_1_label,
                node_2_label="invalid_label",  # Invalid type for node_2_label
                const_law=self.linear_elastic
            )

    def test_invalid_const_law(self):
        # Test that passing an invalid const_law raises the appropriate error
        with self.assertRaises(Exception):
            l.DeformableHinge2(
                idx=6,
                node_1_label=self.node_1_label,
                node_2_label=self.node_2_label,
                const_law="invalid_const_law"  # Invalid type for const_law
            )

class TestNamedConstitutiveLaw(unittest.TestCase):

    def test_string_input(self):
        with self.assertWarns(UserWarning) as cm:
            law = l.NamedConstitutiveLaw("linear elastic")
        self.assertEqual(str(law), "linear elastic")
        self.assertIn("Using a string for constitutive laws is not recommended.", str(cm.warning))

    def test_list_input(self):
        with self.assertWarns(UserWarning) as cm:
            law = l.NamedConstitutiveLaw(["linear elastic", "viscoelastic"])
        self.assertEqual(str(law), "linear elastic, viscoelastic")
        self.assertIn("Using a list for constitutive laws is not recommended.", str(cm.warning))
        
if __name__ == '__main__':
    unittest.main()
