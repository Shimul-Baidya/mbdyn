import unittest
from MBDynLib import *
from MBDynModel import MBDynModel

class TestMBDynModel(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create sample components for testing
        self.data = Data(problem="initial value")
        
        # Create an initial value problem instance
        self.initial_value = InitialValue(
            initial_time=0.0,
            final_time=10.0,
            time_step=0.1,
            tolerance=Tolerance(residual_tolerance=1e-6),
            max_iterations=MaxIterations(max_iterations=10)
        )
        
        # Create control data
        self.control_data = ControlData(
            structural_nodes=2,
            joints=1,
            model="static"
        )
        
        # Create sample nodes
        self.node1 = Node(
            idx=1,
            pos=Position('', [0.0, 0.0, 0.0]),
            orient=Position('', [1.0, 0.0, 0.0]),
            vel=Position('', [0.0, 0.0, 0.0]),
            angular_vel=Position('', [0.0, 0.0, 0.0])
        )
        
        self.node2 = Node(
            idx=2,
            pos=Position('', [1.0, 0.0, 0.0]),
            orient=Position('', [1.0, 0.0, 0.0]),
            vel=Position('', [0.0, 0.0, 0.0]),
            angular_vel=Position('', [0.0, 0.0, 0.0])
        )
        
        # Create a sample element
        self.element = Clamp(
            idx=1,
            node=1
        )

        # Create a sample file driver using FixedStep class from MBDynLib.py
        self.driver = FixedStep(
            idx=1,
            steps_number=100,
            columns_number=3,
            initial_time=0.0,
            time_step=0.01,
            interpolation=FixedStep.InterpolationType.LINEAR,
            pad_zeroes=FixedStep.PadZeroesType.YES,
            bailout=FixedStep.BailoutType.NONE,
            file_name="test.csv"
        )

    def test_model_initialization(self):
        """Test basic model initialization with required components."""
        model = MBDynModel(
            data=self.data,
            problem=self.initial_value,
            control_data=self.control_data,
            nodes=[self.node1, self.node2],
            elements=[self.element]
        )
        
        self.assertIsInstance(model, MBDynModel)
        self.assertEqual(model.data, self.data)
        self.assertEqual(model.problem, self.initial_value)
        self.assertEqual(model.control_data, self.control_data)
        self.assertEqual(len(model.nodes), 2)
        self.assertEqual(len(model.elements), 1)
        self.assertEqual(model.drivers, [])

    def test_add_node(self):
        """Test adding a node to the model."""
        model = MBDynModel(
            data=self.data,
            problem=self.initial_value,
            control_data=self.control_data,
            nodes=[self.node1],
            elements=[self.element]
        )
        
        initial_node_count = len(model.nodes)
        model.add_node(self.node2)
        self.assertEqual(len(model.nodes), initial_node_count + 1)
        self.assertEqual(model.nodes[-1], self.node2)
        
    def test_add_driver(self):
        """Test adding a driver to the model."""
        model = MBDynModel(
            data=self.data,
            problem=self.initial_value,
            control_data=self.control_data,
            nodes=[self.node1, self.node2],
            elements=[self.element]
        )
        
        model.add_driver(self.driver)
        self.assertIsNotNone(model.drivers)
        self.assertEqual(len(model.drivers), 1)
        self.assertEqual(model.drivers[0], self.driver)

    def test_add_element(self):
        """Test adding an element to the model."""
        model = MBDynModel(
            data=self.data,
            problem=self.initial_value,
            control_data=self.control_data,
            nodes=[self.node1, self.node2],
            elements=[]
        )
        
        initial_element_count = len(model.elements)
        model.add_element(self.element)
        self.assertEqual(len(model.elements), initial_element_count + 1)
        self.assertEqual(model.elements[-1], self.element)

    @unittest.skipIf(not imported_pydantic, "Pydantic not available")
    def test_model_validation(self):
        """Test model validation with missing required components."""
        with self.assertRaises(Exception):
            # Missing required nodes
            model = MBDynModel(
                data=self.data,
                problem=self.initial_value,
                control_data=self.control_data,
                # No Nodes
                elements=[self.element]
            )

    def test_str_representation(self):
        """Test string representation of the model."""
        model = MBDynModel(
            data=self.data,
            problem=self.initial_value,
            control_data=self.control_data,
            nodes=[self.node1, self.node2],
            elements=[self.element]
        )
        
        model_str = str(model)
        
        # Verify all required sections are present
        self.assertIn("begin: data;", model_str)
        self.assertIn("begin: nodes;", model_str)
        self.assertIn("begin: elements;", model_str)
        
        # Verify section endings
        self.assertIn("end: data;", model_str)
        self.assertIn("end: nodes;", model_str)
        self.assertIn("end: elements;", model_str)

    def test_model_with_drivers(self):
        """Test model initialization and string representation with drivers."""
        model = MBDynModel(
            data=self.data,
            problem=self.initial_value,
            control_data=self.control_data,
            nodes=[self.node1, self.node2],
            elements=[self.element],
            drivers=[self.driver]
        )
        
        model_str = str(model)
        self.assertIn("begin: drivers;", model_str)
        self.assertIn("end: drivers;", model_str)
        # Verify driver content is included
        self.assertIn("fixed step", model_str.lower())

    def test_multiple_drivers(self):
        """Test model with multiple drivers."""
        # Create a second driver using VariableStep class
        variable_step_driver = VariableStep(
            idx=2,
            channels_number=3,
            interpolation=FixedStep.InterpolationType.LINEAR,
            pad_zeroes=FixedStep.PadZeroesType.YES,
            bailout=FixedStep.BailoutType.NONE,
            file_name="test_variable.csv"
        )
        
        model = MBDynModel(
            data=self.data,
            problem=self.initial_value,
            control_data=self.control_data,
            nodes=[self.node1, self.node2],
            elements=[self.element],
            drivers=[self.driver, variable_step_driver]
        )
        
        self.assertEqual(len(model.drivers), 2)
        model_str = str(model)
        self.assertIn("fixed step", model_str.lower())
        self.assertIn("variable step", model_str.lower())

if __name__ == '__main__':
    unittest.main()