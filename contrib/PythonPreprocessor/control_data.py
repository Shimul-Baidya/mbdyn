from abc import ABC, abstractmethod
from MBDynLib import *
from typing import Optional, Tuple, Union, List, Literal, Any

imported_pydantic = False
try:
    from pydantic import BaseModel, ConfigDict, field_validator, FieldValidationInfo, model_validator
    imported_pydantic = True
    class _EntityBase(BaseModel):
        """Configuration for Entity with pydantic available"""
        model_config = ConfigDict(extra='forbid',
                                  use_attribute_docstrings=True)

except ImportError:
    class _EntityBasePlaceholder:
        """Placeholder with minimal functionality for running a correct model when some libraries aren't available"""

        def __init__(self, *args, **kwargs):
            if len(args) > 0:
                raise TypeError(
                    'MBDyn entities cannot be initialized using positional arguments')
            for key, value in kwargs.items():
                setattr(self, key, value)

    def placeholder(*args, **kwargs):
        """Ignores all arguments"""
        return None

    # HACK: This forces code analysis to always use the definition with pydantic
    exec('_EntityBase = _EntityBasePlaceholder')
    exec('ConfigDict = placeholder')

    def identity_decorator(*args, **kwargs):
        """Ignores all decorator arguments and returns the wrapped function unchanged"""
        def identity(func):
            return func
        return identity

    field_validator = identity_decorator
    model_validator = identity_decorator


class MBEntity(_EntityBase, ABC):
    """Base class for every 'thing' to put in MBDyn file, other than numbers"""

    @abstractmethod
    def __str__(self) -> str:
        """Has to be overridden to output the MBDyn syntax"""
        pass


class Print(MBEntity):
    items: List[Literal[
        "dof stats", "dof description", "equation description", "description", 
        "element connection", "node connection", "connection", "all", "none"
    ]] = []
    item_to_file: Optional[List[bool]] = None  

    def __str__(self):
        s = "print: "

        # Check if item_to_file has the same length as items
        item_to_file_filled = self.item_to_file or [False] * len(self.items)
        if len(item_to_file_filled) < len(self.items):
            item_to_file_filled.extend([False] * (len(self.items) - len(item_to_file_filled)))
            
        # Loop through each item and build the string with appropriate formatting
        for idx, item in enumerate(self.items):
            s += f"{item}"
            # Check if 'to file' is specified for this item using item_to_file_filled
            if item_to_file_filled[idx]:  
                s += ", to file"
            # Add a comma between items except for the last item
            if idx < len(self.items) - 1:  
                s += ", "
        return s
    
class OutputResults(MBEntity):
    '''
    This deprecated statement was intended for producing output in formats compatible with other software.
    Most of them are produced in form of post-processing, based on the default raw output.
    '''

    file_format: Literal["classic", "classic64", "nc4", "nc4classic"] = "nc4"
    sync: bool = False
    text: bool = False

    def __str__(self):
        s = f'output results: netcdf, {self.file_format}'
        if self.sync:
            s += ',\n\tsync'
        else: 
            s += ',\n\tno sync'
        if self.text:
            s += ', text'
        else: 
            s += ', no text'
        return s
    
class ConstRBK(MBEntity):
    position: Optional[Position2] = None
    orientation: Optional[Position2] = None
    velocity: Optional[Position2] = None
    angular_velocity: Optional[Position2] = None
    acceleration: Optional[Position2] = None
    angular_acceleration: Optional[Position2] = None

    def __str__(self):
        s = 'const'
        if self.position:
            s += f',\n\tposition, {self.position}'
        if self.orientation:
            s += f',\n\torientation, {self.orientation}'
        if self.velocity:
            s += f',\n\tvelocity, {self.velocity}'
        if self.angular_velocity:
            s += f',\n\tangular velocity, {self.angular_velocity}'
        if self.acceleration:
            s += f',\n\tacceleration, {self.acceleration}'
        if self.angular_acceleration:
            s += f',\n\tangular acceleration, {self.angular_acceleration}'
        return s

class DriveRBK(MBEntity):
    position: Optional[TplDriveCaller] = None
    orientation: Optional[TplDriveCaller] = None
    velocity: Optional[TplDriveCaller] = None
    angular_velocity: Optional[TplDriveCaller] = None
    acceleration: Optional[TplDriveCaller] = None
    angular_acceleration: Optional[TplDriveCaller] = None

    def __str__(self):
        s = 'drive'
        if self.position:
            s += f',\n\tposition, {self.position}'
        if self.orientation:
            s += f',\n\torientation, {self.orientation}'
        if self.velocity:
            s += f',\n\tvelocity, {self.velocity}'
        if self.angular_velocity:
            s += f',\n\tangular velocity, {self.angular_velocity}'
        if self.acceleration:
            s += f',\n\tacceleration, {self.acceleration}'
        if self.angular_acceleration:
            s += f',\n\tangular acceleration, {self.angular_acceleration}'
        return s


class ControlData(MBEntity):
    '''
    This section is read by the manager of all the bulk simulation data, namely the nodes, the drivers and
    the elements. It is used to set some global parameters closely related to the behavior of these entities,
    to tailor the initial assembly of the joints in case of structural simulations, and to tell the data manager
    how many entities of every type it should expect from the following sections. Historically this is due to
    the fact that the data structure for nodes and elements is allocated at the beginning with ﬁxed size. This
    is going to change, giving raise to a “free” and resizeable structure. But this practice is to be considered
    reliable since it allows a sort of double-check on the entities that are inserted.
    '''

    use_auto_differentiation: Optional[Union[bool, int]] = False    # 0 / 1 / True / False
    skip_initial_joint_assembly: Optional[Union[bool, int]] = False    # 0 / 1 / True / False
    simulation_title: Optional[str] = None
    print: Optional[Print] = None
    output_frequency: Optional[Union[int, MBVar]] = None
    output_meter: Optional[Union[DriveCaller, DriveCaller2]] = None
    output_results: Optional[OutputResults] = None
    default_orientation: Union[Literal["euler123", "euler313", "euler321", "orientation vector", "orientation matrix"]] = "euler123"
    model: Literal["static"] = "static"
    rbk_data: Optional[Union[ConstRBK, DriveRBK]] = None

    ## Model Counter Cards
    # Nodes
    abstract_nodes: Optional[Union[int, str]] = None
    electric_nodes: Optional[Union[int, str]] = None
    hydraulic_nodes: Optional[Union[int, str]] = None
    parameter_nodes: Optional[Union[int, str]] = None
    structural_nodes: Optional[Union[int, str]] = None
    thermal_nodes: Optional[Union[int, str]] = None

    # Drivers
    file_drivers: Optional[Union[int, str]] = None

    # Elements
    aerodynamic_elements: Optional[Union[int, str]] = None
    aeromodals: Optional[Union[int, str]] = None
    air_properties: Optional[Union[int, str]] = None
    automatic_structural_elements: Optional[Union[int, str]] = None
    beams: Optional[Union[int, str]] = None
    bulk_elements: Optional[Union[int, str]] = None
    electric_bulk_elements: Optional[Union[int, str]] = None
    electric_elements: Optional[Union[int, str]] = None
    external_elements: Optional[Union[int, str]] = None
    forces: Optional[Union[int, str]] = None
    genels: Optional[Union[int, str]] = None
    gravity: Optional[Union[int, str]] = None
    hydraulic_elements: Optional[Union[int, str]] = None
    induced_velocity_elements: Optional[Union[int, str]] = None
    joints: Optional[Union[int, str]] = None
    joint_regularizations: Optional[Union[int, str]] = None
    loadable_elements: Optional[Union[int, str]] = None
    output_elements: Optional[Union[int, str]] = None
    solids: Optional[Union[int, str]] = None
    surface_loads: Optional[Union[int, str]] = None
    rigid_bodies: Optional[Union[int, str]] = None

    @field_validator('use_auto_differentiation', mode='after')
    def set_use_auto_differentiation(cls, v):
        if isinstance(v, (int, bool)):  # Check if v is an int or a bool
            if v in [0, False]:
                return None  # Return None for 0 or False
            elif v in [1, True]:
                return "use auto differentiation"  # Return specific string for 1 or True
            else:
                raise ValueError("use_auto_differentiation must be 0, 1, True, or False.")
        else:
            raise TypeError("use_auto_differentiation must be of type int or bool.")

    @field_validator('skip_initial_joint_assembly', mode='after')
    def set_skip_initial_joint_assembly(cls, v):
        if isinstance(v, (int, bool)):  # Check if v is an int or a bool
            if v in [0, False]:
                return None  # Return None for 0 or False
            elif v in [1, True]:
                return "skip initial joint assembly"  # Return specific string for 1 or True
            else:
                raise ValueError("skip_initial_joint_assembly must be 0, 1, True, or False.")
        else:
            raise TypeError("skip_initial_joint_assembly must be of type int or bool.")

    def __str__(self):
        s = 'begin: control data;\n'
        if self.use_auto_differentiation:
            s += f'\tuse automatic differentiation;\n'
        if self.skip_initial_joint_assembly:
            s += f'\tskip initial joint assembly;\n'
        if self.simulation_title:
            s += f'\ttitle: {self.simulation_title};\n'
        if self.print:
            s += f'\t{self.print};\n'
        if self.output_frequency:
            s += f'\toutput frequency: {self.output_frequency};\n'
        if self.output_meter:
            s += f'\toutput meter: {self.output_meter};\n'
        if self.output_results:
            s += f'\t{self.output_results};\n'

        s += f'\tdefault orientation: {self.default_orientation};\n'
        s += f'\tmodel: {self.model};\n'

        if self.rbk_data:
            s += f'\trigid body kinematics: {self.rbk_data};\n'

        # Model Counter Cards - Nodes
        if self.abstract_nodes:
            s += f'\tabstract nodes: {self.abstract_nodes};\n'
        if self.electric_nodes:
            s += f'\telectric nodes: {self.electric_nodes};\n'
        if self.hydraulic_nodes:
            s += f'\thydraulic nodes: {self.hydraulic_nodes};\n'
        if self.parameter_nodes:
            s += f'\tparameter nodes: {self.parameter_nodes};\n'
        if self.structural_nodes:
            s += f'\tstructural nodes: {self.structural_nodes};\n'
        if self.thermal_nodes:
            s += f'\tthermal nodes: {self.thermal_nodes};\n'
        
        # Model Counter Cards - Drivers
        if self.file_drivers:
            s += f'\tfile drivers: {self.file_drivers};\n'
        
        # Model Counter Cards - Elements
        if self.aerodynamic_elements:
            s += f'\taerodynamic elements: {self.aerodynamic_elements};\n'
        if self.aeromodals:
            s += f'\taeromodals: {self.aeromodals};\n'
        if self.air_properties:
            s += f'\tair properties: {self.air_properties};\n'
        if self.automatic_structural_elements:
            s += f'\tautomatic structural elements: {self.automatic_structural_elements};\n'
        if self.beams:
            s += f'\tbeams: {self.beams};\n'
        if self.bulk_elements:
            s += f'\tbulk elements: {self.bulk_elements};\n'
        if self.electric_bulk_elements:
            s += f'\telectric bulk elements: {self.electric_bulk_elements};\n'
        if self.electric_elements:
            s += f'\telectric elements: {self.electric_elements};\n'
        if self.external_elements:
            s += f'\texternal elements: {self.external_elements};\n'
        if self.forces:
            s += f'\tforces: {self.forces};\n'
        if self.genels:
            s += f'\tgenels: {self.genels};\n'
        if self.gravity:
            s += f'\tgravity: {self.gravity};\n'
        if self.hydraulic_elements:
            s += f'\thydraulic elements: {self.hydraulic_elements};\n'
        if self.induced_velocity_elements:
            s += f'\tinduced velocity elements: {self.induced_velocity_elements};\n'
        if self.joints:
            s += f'\tjoints: {self.joints};\n'
        if self.joint_regularizations:
            s += f'\tjoint regularizations: {self.joint_regularizations};\n'
        if self.loadable_elements:
            s += f'\tloadable elements: {self.loadable_elements};\n'
        if self.output_elements:
            s += f'\toutput elements: {self.output_elements};\n'
        if self.solids:
            s += f'\tsolids: {self.solids};\n'
        if self.surface_loads:
            s += f'\tsurface loads: {self.surface_loads};\n'
        if self.rigid_bodies:
            s += f'\trigid bodies: {self.rigid_bodies};\n'

        s += 'end: control data;'
        return s
