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
    default_orientation: Optional[Union[Literal["euler123", "euler313", "euler321", "orientation vector", "orientation matrix"]]] = "euler123"
    model: Literal["static"] = "static"
    rbk_data: Optional[Union[ConstRBK, DriveRBK]] = None