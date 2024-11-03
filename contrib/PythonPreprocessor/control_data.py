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
    