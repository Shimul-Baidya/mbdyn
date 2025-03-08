#
#MBDyn (C) is a multibody analysis code.
#http://www.mbdyn.org
#
#Copyright (C) 1996-2023
#
#Pierangelo Masarati	<pierangelo.masarati@polimi.it>
#Paolo Mantegazza	<paolo.mantegazza@polimi.it>
#
#Dipartimento di Ingegneria Aerospaziale - Politecnico di Milano
#via La Masa, 34 - 20156 Milano, Italy
#http://www.aero.polimi.it
#
#Changing this copyright notice is forbidden.
#
#This program is free software; you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation (version 2 of the License).
#
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA



#COPYRIGHT (C) 2016
#
#Marco Morandini <marco.morandini@polimi.it>
#Mattia Alioli   <mattia.alioli@polimi.it>
#
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2 of the License, or (at your option) any later version.
#
#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#Lesser General Public License for more details.
#
#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA.


from abc import ABC, abstractmethod
import builtins
from enum import Enum
from numbers import Number, Integral
import sys
from typing import Optional, Tuple, Union, List, Literal, Any, ClassVar, Tuple
import warnings


assert sys.version_info >= (3,6), 'Syntax for variable annotations (PEP 526) was introduced in Python 3.6'

declared_ConstMBVars = {}
declared_IfndefMBVars = {}
declared_MBVars = {}

MBDynLib_simplify = True

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
    validate_call = identity_decorator


class MBEntity(_EntityBase, ABC):
    """Base class for every 'thing' to put in MBDyn file, other than numbers"""

    @abstractmethod
    def __str__(self) -> str:
        """Has to be overridden to output the MBDyn syntax"""
        pass


def errprint(*args, **kwargs):
    print(*args, file = sys.stderr, **kwargs)

def get_value(x):
    if isinstance(x, expression):
        return x.__get__()
    else:
        return x

def simplify_null_element_multiplication(l, r):
    if MBDynLib_simplify:
        if l == 0 or r == 0:
            return True
        else:
            return False
    else:
        return False

def simplify_null_element_division(l, r):
    assert get_value(r) != 0, (
        'Error, division by zero: \'' + str(l) + ' / ' + str(r) + 
        '\'\n')
    if MBDynLib_simplify:
        if l == 0:
            return True
        else:
            return False
    else:
        return False

def simplify_neutral_element(l, r, op, ne):
    if MBDynLib_simplify:
        #if get_value(l) == ne:
        if l == ne:
            return r
        #elif get_value(r) == ne:
        elif r == ne:
            return l
        else:
            return op(l, r)
    else:
        return op(l, r)

class expression:
    def __init__(self):
        pass
    def __neg__(self):
        return negative(self)
    def __add__(self, other):
            return simplify_neutral_element(self, other, addition, 0) #addition(self, other)
    def __sub__(self, other):
            return simplify_neutral_element(self, other, subtraction, 0) #subtraction(self, other)
    def __pow__(self, other):
            return power(self, other)
    def __mul__(self, other):
            if simplify_null_element_multiplication(self, other):
                return 0
            else:
                return simplify_neutral_element(self, other, multiplication, 1) #multiplication(self, other)
    def __truediv__(self, other):
            if simplify_null_element_division(self, other):
                return 0
            else:
                return division(self, other)
    def __radd__(self, other):
            return simplify_neutral_element(other, self, addition, 0) #addition(other, self)
    def __rsub__(self, other):
            return simplify_neutral_element(other, self, subtraction, 0) #subtraction(other, self)
    def __rmul__(self, other):
            if simplify_null_element_multiplication(other, self):
                return 0
            else:
                return simplify_neutral_element(other, self, multiplication, 1) #multiplication(other, self)
    def __rtruediv__(self, other):
            if simplify_null_element_division(other, self):
                return 0
            else:
                return division(other, self)

class negative(expression):
    def __init__(self, left):
        expression.__init__(self)
        self.left = left
    def __get__(self):
        return -get_value(self.left)
    def __str__(self):
        ls = str(self.left)
        if isinstance(self.left, terminal_expression) or isinstance(self.right, MBVar):
            pass
        elif isinstance(self.right, expression):
            ls = '(' + str(self.left) +')'
        return '-' + ls

import math
class sin(expression):
    def __init__(self, left):
        expression.__init__(self)
        self.left = left
    def __get__(self):
        return math.sin(get_value(self.left))
    def __str__(self):
        ls = str(self.left)
        return 'sin(' + ls + ')'

class cos(expression):
    def __init__(self, left):
        expression.__init__(self)
        self.left = left
    def __get__(self):
        return math.cos(get_value(self.left))
    def __str__(self):
        ls = str(self.left)
        return 'cos(' + ls + ')'

class tan(expression):
	def __init__(self, left):
		expression.__init__(self)
		self.left = left
	def __get__(self):
		return math.tan(get_value(self.left))
	def __str__(self):
		ls = str(self.left)
		return 'tan(' + ls + ')'

class asin(expression):
	def __init__(self, left):
		expression.__init__(self)
		self.left = left
	def __get__(self):
		return math.asin(get_value(self.left))
	def __str__(self):
		ls = str(self.left)
		return 'asin(' + ls + ')'

class acos(expression):
	def __init__(self, left):
		expression.__init__(self)
		self.left = left
	def __get__(self):
		return math.acos(get_value(self.left))
	def __str__(self):
		ls = str(self.left)
		return 'acos(' + ls + ')'

class sqrt(expression):
	def __init__(self, left):
		expression.__init__(self)
		self.left = left
	def __get__(self):
		return math.sqrt(get_value(self.left))
	def __str__(self):
		ls = str(self.left)
		return 'sqrt(' + ls + ')'

class terminal_expression(expression):
    def __init__(self, value):
        expression.__init__(self)
        self.value = value
    def __get___(self):
        return self.value
    def __str__(self):
        return str(self.value)

class binary_expression(expression):
    def __init__(self, left, right):
        expression.__init__(self)
        self.left = left
        self.right = right
    def __trunc__(self):
        y = self.__get__()
        assert isinstance(y, int), (
                'Error, __trunc__  required for expression \n\'' + 
                str(self) + 
                '\'\nof type ' + str(type(y)) +
                ' \n')
        return y
    def __index__(self):
        return self.__trunc__()

class atan2(binary_expression):
	def __init__(self, left, right):
		binary_expression.__init__(self, left, right)
	def __get__(self):
		return math.atan2(get_value(self.left), get_value(self.right))
	def __str__(self):
		ls = str(self.left)
		rs = str(self.right)
		return 'atan2(' + ls + ', ' + rs + ')'

class addition(binary_expression):
    def __init__(self, left, right):
        binary_expression.__init__(self, left, right)
    def __get__(self):
        return get_value(self.left) + get_value(self.right)
    def __str__(self):
        ls = str(self.left)
        rs = str(self.right)
        return ls + ' + ' + rs
            
class subtraction(binary_expression):
    def __init__(self, left, right):
        binary_expression.__init__(self, left, right)
    def __get__(self):
        return get_value(self.left) - get_value(self.right)
    def __str__(self):
        ls = str(self.left)
        rs = str(self.right)
        return ls + ' - ' + rs
            
class multiplication(binary_expression):
    def __init__(self, left, right):
        binary_expression.__init__(self, left, right)
    def __get__(self):
        return get_value(self.left) * get_value(self.right)
    def __str__(self):
        ls = str(self.left)
        rs = str(self.right)
        if isinstance(self.left, addition) or isinstance(self.left, subtraction):
            ls = '(' + ls + ')'
        if isinstance(self.right, addition) or isinstance(self.right, subtraction):
            rs = '(' + rs + ')'
        return ls + ' * ' + rs
            
class division(binary_expression):
    def __init__(self, left, right):
        binary_expression.__init__(self, left, right)
    def __get__(self):
        return get_value(self.left) / get_value(self.right)
    def __str__(self):
        ls = str(self.left)
        rs = str(self.right)
        if isinstance(self.left, addition) or isinstance(self.left, subtraction):
            ls = '(' + ls + ')'
        if isinstance(self.right, terminal_expression) or isinstance(self.right, MBVar) or isinstance(self.right, power):
            pass
        elif isinstance(self.right, expression):
            rs = '(' + rs + ')'
        return ls + ' / ' + rs

class power(binary_expression):
    def __init__(self, left, right):
        binary_expression.__init__(self, left, right)
    def __get__(self):
        return pow(get_value(self.left), get_value(self.right))
    def __str__(self):
        ls = str(self.left)
        rs = str(self.right)
        if isinstance(self.left, terminal_expression) or isinstance(self.right, MBVar):
            pass
        elif isinstance(self.left, expression):
            ls = '(' + ls + ')'
        if isinstance(self.right, terminal_expression) or isinstance(self.right, MBVar):
            pass
        elif isinstance(self.right, expression):
            rs = '(' + rs + ')'
        return ls + ' ^ ' + rs


# Enum entries need annotated type to find descriptions for documentation
class MBVarType(str, Enum):
    """Built-in types in math parser"""
    BOOL: str = 'bool'
    INTEGER: str = 'integer'
    REAL: str = 'real'
    STRING: str = 'string'

class MBVarModifiers(str, Enum):
    CONST: str = 'const'
    DEFINE: str = 'ifndef const'

class MBVar(MBEntity, terminal_expression):
    name: str
    var_type: str
    expression: Any

    var_types: ClassVar[Tuple[str]] = tuple([t.value for t in MBVarType] +\
                                  [f'{MBVarModifiers.CONST} {t.value}' for t in MBVarType] +\
                                  [f'{MBVarModifiers.DEFINE} {t.value}' for t in MBVarType])

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator('var_type')
    def validate_var_type(cls, v):
        assert v in cls.var_types, (
            f'\n-------------------\nERROR: MBVar: unknown variable type {v}\n\t' +
            '\n-------------------\n'
        )
        return v

    @model_validator(mode='after')
    def validate_declarations(self):
        assert self.name not in declared_ConstMBVars, (
            '\n-------------------\nERROR: re-defining an already declared const variable:\n\t' +
            f'{self.var_type} {self.name}\n-------------------\n'
        )
        
        assert self.name not in declared_IfndefMBVars, (
            '\n-------------------\nERROR: re-defining an already declared ifndef variable:\n\t' +
            f'{self.var_type} {self.name}\n-------------------\n'
        )
        return self

    def __init__(self, name: str, var_type: str, expression: Any):
        super().__init__(name=name, var_type=var_type, expression=expression)
        self.declare()

    def __get__(self):
        return get_value(self.expression)

    def __trunc__(self):
        y = self.__get__()
        assert isinstance(y, int), (
            f'Error, __trunc__ required for expression \n\'{self}\'\nof type {type(y)}\n'
        )
        return self.expression.__trunc__()

    def __index__(self):
        return self.expression.__trunc__()

    def __str__(self):
        return str(self.name)
    
    def __repr__(self):
        # This ensures that when the object is used in lists or other contexts,
        # it still outputs just the name
        return self.__str__()

    def __lt__(self, other):
        return self.__get__() < other

    def __gt__(self, other):
        return self.__get__() > other

    def __eq__(self, other):
        return self.__get__() == other

    def __le__(self, other):
        return self.__get__() <= other

    def __ge__(self, other):
        return self.__get__() >= other

    def declare(self):
        if self.name in declared_MBVars:
            assert declared_MBVars[self.name].var_type == self.var_type, (
                '\n-------------------\nERROR: re-defining an already declared variable of type ' +
                f'{declared_MBVars[self.name].var_type}\nwith different type {self.var_type}\n' +
                '\n-------------------\n'
            )
            if 'string' in self.var_type:
                print(f'set: {self.name} = "{str(self.expression)}";')
            else:
                print(f'set: {self.name} = {str(self.expression)};')
        else:
            declared_MBVars[self.name] = self
            if 'string' in self.var_type:
                print(f'set: {self.var_type} {self.name} = "{str(self.expression)}";')
            else:
                print(f'set: {self.var_type} {self.name} = {str(self.expression)};')
        setattr(builtins, self.name, self)

    def __str__(self):
        return self.name
    
    def __repr__(self):
        return self.name

class ConstMBVar(MBVar):
    def __init__(self, name: str, var_type: str, value: Any):
        super().__init__(name=name, var_type=f'const {var_type}', expression=value)

    def declare(self):
        super().declare()
        declared_ConstMBVars[self.name] = self

class IfndefMBVar(MBVar):
    def __init__(self, name: str, var_type: str, value: Any):
        if name not in declared_MBVars:
            super().__init__(name=name, var_type=f'ifndef {var_type}', expression=value)


class null(MBEntity):
    def __str__(self):
        return 'null'

class eye(MBEntity):
    def __str__(self):
        return 'eye'

class Reference:
    def __init__(self, idx, pos, orient, vel, angvel):
        assert isinstance(pos, Position), (
            '\n-------------------\nERROR:'+
            ' the position of a reference must be ' +
            ' an instance of the Position class;' +
            '\n-------------------\n')
        assert isinstance(orient, Position), (
            '\n-------------------\nERROR:' +
            ' the orientation of a reference must be ' +
            ' an instance of the Position class;' +
            '\n-------------------\n')
        assert isinstance(vel, Position), (
            '\n-------------------\nERROR:' +
            ' the velocity of a reference must be ' +
            ' an instance of the Position class;' +
            '\n-------------------\n')
        assert isinstance(angvel, Position), (
            '\n-------------------\nERROR:' +
            ' the angulare velocity of a reference must be ' +
            ' an instance of the Position class;' +
            '\n-------------------\n')
        self.idx = idx
        self.position = pos
        self.orientation = orient
        self.velocity = vel
        self.angular_velocity = angvel
    def __str__(self):
        s = 'reference: '
        s = s + str(self.idx) + ', \n'
        s = s + '\t' + str(self.position) + ',\n'
        s = s + '\t' + str(self.orientation) + ',\n'
        s = s + '\t' + str(self.velocity) + ',\n'
        s = s + '\t' + str(self.angular_velocity) + ';\n'
        return s

class Position:
    def __init__(self, ref, rel_pos):
        self.reference = ref
        if isinstance(rel_pos, list):
            self.relative_position = rel_pos
        else:
            self.relative_position = [rel_pos]
    def __str__(self):
        s = ''
        if self.reference != '':
            s = 'reference, ' + str(self.reference) + ', '
        s = s + ', '.join(str(i) for i in self.relative_position)
        return s
    def isnull(self):
        return (self.reference == '') and isinstance(self.relative_position[0], null)
    def iseye(self):
        return (self.reference == '') and isinstance(self.relative_position[0], eye)

# TODO: Rename to Position when all are moved
class Position2(MBEntity):
    """Position definition for MBDyn elements"""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)  # Add this line to allow expression type
    
    relative_position: Union[List[Union[float, MBVar, null, eye, expression]], 
                           List[List[Union[float, MBVar, null, eye, expression]]]]
    reference: Union['Reference2', Literal['global', 'node', 'other node', '']]

    @field_validator('relative_position', mode='before')
    def ensure_list(cls, v):
        if not isinstance(v, list):
            return [v]
        return v

    @field_validator('reference')
    def validate_reference(cls, v):
        if isinstance(v, str):
            if v not in {'global', 'node', 'other node', ''}:
                raise ValueError("Invalid literal for reference")
        elif not isinstance(v, Reference2):
            raise ValueError("reference must be either a Reference2 instance or one of the specified strings")
        return v

    def __str__(self):
        s = ''
        if self.reference != '':
            s = 'reference, ' + str(self.reference) + ', '
        s = s + ', '.join(str(i) for i in self.relative_position)
        return s

    def isnull(self) -> bool:
        return (self.reference == '') and isinstance(self.relative_position[0], null)

    def iseye(self) -> bool:
        return (self.reference == '') and isinstance(self.relative_position[0], eye)
    
# TODO: Rename to Reference when all are moved
class Reference2(MBEntity):
    idx: Union[int, MBVar]
    position: Position2
    orientation: Position2
    velocity: Position2
    angular_velocity: Position2    
    def __str__(self):
        s = 'reference: '
        s = s + str(self.idx) + ', \n'
        s = s + '\t' + str(self.position) + ',\n'
        s = s + '\t' + str(self.orientation) + ',\n'
        s = s + '\t' + str(self.velocity) + ',\n'
        s = s + '\t' + str(self.angular_velocity) + ';\n'
        return s

if imported_pydantic:
    Position2.model_rebuild()

class Node:
    def __init__(self, idx, pos, orient, vel, angular_vel, node_type = 'dynamic',
            scale = 'default', output = 'yes'):
        assert isinstance(pos, Position), (
            '\n-------------------\nERROR:' + 
            ' the initial position of a node must be ' +  
            ' an instance of the Position class;' + 
            '\n-------------------\n')
        assert isinstance(orient, Position), (
            '\n-------------------\nERROR:' + 
            ' the initial orientation of a node must be ' +  
            ' an instance of the Position class;' + 
            '\n-------------------\n')
        assert isinstance(vel, Position), (
            '\n-------------------\nERROR:' + 
            ' the initial velocity of a node must be ' +  
            ' an instance of the Position class;' + 
            '\n-------------------\n')
        assert isinstance(angular_vel, Position), (
            '\n-------------------\nERROR:' + 
            ' the initial angular velocity of a node must be ' +  
            ' an instance of the Position class;' + 
            '\n-------------------\n')
        assert node_type in ('dynamic', 'static',), (
            '\n-------------------\nERROR:' + 
            ' unrecognised or unsupported node type;' + 
            '\n-------------------\n')
        self.idx = idx
        self.position = pos
        self.orientation = orient
        self.velocity = vel
        self.angular_velocity = angular_vel
        self.node_type = node_type
        self.scale = scale
        self.output = output
    def __str__(self):
        s = 'structural: ' + str(self.idx) + ', ' + str(self.node_type) + ',\n'
        s = s + '\t' + str(self.position) + ',\n'
        s = s + '\t' + str(self.orientation) + ',\n'
        s = s + '\t' + str(self.velocity) + ',\n'
        s = s + '\t' + str(self.angular_velocity)
        if self.scale != 'default':
            s = s + ',\n\tscale, ' + str(self.scale)
        if self.output != 'yes':
            s = s + ',\n\toutput, ' + str(self.output)
        s = s + ';\n'
        return s

class DynamicNode(Node):
    def __init__(self, idx, pos, orient, vel, angular_vel):
        Node.__init__(self, idx, pos, orient, vel, angular_vel, 'dynamic')

class StaticNode(Node):
    def __init__(self, idx, pos, orient, vel, angular_vel):
        Node.__init__(self, idx, pos, orient, vel, angular_vel, 'static')

class DisplacementNode():
    def __init__(self, idx, pos, vel, node_type = 'dynamic',
            scale = 'default', output = 'yes'):
        self.idx = idx
        self.position = pos
        self.velocity = vel
        self.node_type = node_type
        self.scale = scale
        self.output = output
    def __str__(self):
        s = 'structural: ' + str(self.idx) + ', ' + str(self.node_type) + ' displacement,\n'
        s = s + '\t' + str(self.position) + ',\n'
        s = s + '\t' + str(self.velocity)
        if self.scale != 'default':
            s = s + ',\n\t scale, ' + str(self.scale)
        if self.output != 'yes':
            s = s + ',\n\toutput, ' + str(self.output)
        s = s + ';\n'
        return s

class DynamicDisplacementNode(DisplacementNode):
    def __init__(self, idx, pos, vel):
        DisplacementNode.__init__(self, idx, pos, vel, 'dynamic')

class StaticDisplacementNode(DisplacementNode):
    def __init__(self, idx, pos, vel):
        DisplacementNode.__init__(self, idx, pos, vel, 'static')

# Change name to Node when all are moved
class Node2(MBEntity):
    idx: Union[int, MBVar]
    position: Position2
    orientation: Position2
    velocity: Position2
    angular_velocity: Position2
    node_type: str = 'dynamic'
    scale: Optional[Union[str, float, MBVar]] = 'default'
    output: Optional[Union[Literal['yes', 'no'], bool, int]] = 'yes'
    def __str__(self):
        s = f"structural: {self.idx}, {self.node_type},\n"
        s += f"\t{self.position},\n"
        s += f"\t{self.orientation},\n"
        s += f"\t{self.velocity},\n"
        s += f"\t{self.angular_velocity}"
        if self.scale != 'default':
            s += f",\n\tscale, {self.scale}"
        if self.output != 'yes':
            s += f",\n\toutput, {self.output}"
        return s
    
class DynamicNode2(Node2):
    accelerations: Optional[Union[Literal['yes', 'no'], bool]] = None
    def __init__(self, idx, pos, orient, vel, angular_vel, accelerations=None):
        super().__init__(idx=idx, position=pos, orientation=orient, velocity=vel, angular_velocity=angular_vel, node_type='dynamic')
        self.accelerations = accelerations
    def __str__(self):
        s = super().__str__()
        if self.accelerations is not None:
            s += f",\n\taccelerations, {self.accelerations}"
        s += ';\n'
        return s

class StaticNode2(Node2):
    def __init__(self, idx, pos, orient, vel, angular_vel):
        super().__init__(idx=idx, position=pos, orientation=orient, velocity=vel, angular_velocity=angular_vel, node_type='static')
    def __str__(self):
        return super().__str__() + ';\n'

class ModalNode(Node2):
    accelerations: Optional[Union[Literal['yes', 'no'], bool]] = None
    def __init__(self, idx, pos, orient, vel, angular_vel, accelerations=None):
        super().__init__(idx=idx, position=pos, orientation=orient, velocity=vel, angular_velocity=angular_vel, node_type='modal')
        self.accelerations = accelerations
    def __str__(self):
        s = super().__str__()
        if self.accelerations is not None:
            s += f",\n\taccelerations, {self.accelerations}"
        s += ';\n'
        return s

class DisplacementNode2(MBEntity):
    idx: Union[int, MBVar]
    position: Position2
    velocity: Position2
    node_type: str = 'dynamic'
    scale: Optional[Union[str, float, MBVar]] = 'default'
    output: Optional[Union[Literal['yes', 'no'], bool, int]] = 'yes'
    def __str__(self):
        s = f"structural: {self.idx}, {self.node_type} displacement,\n"
        s += f"\t{self.position},\n"
        s += f"\t{self.velocity}"
        if self.scale != 'default':
            s += f",\n\tscale, {self.scale}"
        if self.output != 'yes':
            s += f",\n\toutput, {self.output}"
        return s

class DynamicDisplacementNode2(DisplacementNode2):
    accelerations: Optional[Union[Literal['yes', 'no'], bool]] = None
    def __init__(self, idx, pos, vel, accelerations=None):
        super().__init__(idx=idx, position=pos, velocity=vel, node_type='dynamic')
        self.accelerations = accelerations
    def __str__(self):
        s = super().__str__()
        if self.accelerations is not None:
            s += f",\n\taccelerations, {self.accelerations}"
        return s + ';\n'

class StaticDisplacementNode2(DisplacementNode2):
    def __init__(self, idx, pos, vel):
        super().__init__(idx=idx, position=pos, velocity=vel, node_type='static')
    def __str__(self):
        return super().__str__() + ';\n'

class ModalDisplacementNode(DisplacementNode2):
    accelerations: Optional[Union[Literal['yes', 'no'], bool]] = None
    def __init__(self, idx, pos, vel, accelerations=None):
        super().__init__(idx=idx, position=pos, velocity=vel, node_type='modal')
        self.accelerations = accelerations
    def __str__(self):
        s = super().__str__()
        if self.accelerations is not None:
            s += f",\n\taccelerations, {self.accelerations}"
        return s + ';\n'
    
class PointMass:
    def __init__(self, idx, node, mass, output = 'yes'):
        self.idx = idx
        self.node = node
        self.mass = mass
        self.output = output
    def __str__(self):
        s = 'body: ' + str(self.idx) + ', ' + str(self.node) + ', ' + str(self.mass)
        if self.output != 'yes':
            s = s + ', output, ' + str(self.output)
        s = s + ';\n'
        return s

class Element:
    idx = -1

# TODO: Rename to Element when all are moved
class Element2(MBEntity):
    """
    Abstract base class for all elements
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    idx: Union[MBVar, int]
    output: Optional[Union[bool, str, int]] = 'yes'
    @field_validator('output')
    def validate_output(cls, v):
        if isinstance(v, str):
            if v not in {'yes', 'no'}:
                raise ValueError("output must be 'yes', 'no', or a boolean value")
        elif not isinstance(v, (bool, int)):
            raise ValueError("output must be a boolean, integer, or one of 'yes'/'no'")
        return v

    @abstractmethod
    def element_type(self) -> str:
        """Every element class must define this to return its MBDyn syntax name"""
        raise NotImplementedError("called elelemt_type of abstract Element")

    def element_header(self) -> str:
        """common syntax for start of any element"""
        return f'{self.element_type()}: {self.idx}'
    
    def element_footer(self) -> str:
        s = ''
        if self.output != 'yes':
            s = s + f''',\n\toutput, {self.output}'''
        s = s + ';\n'
        return s

    @staticmethod
    def check_unit_vector3(value: List[Union[float, MBVar]]):
        if not len(value) == 3:
            raise ValueError("relative_direction must be a 3-dimensional vector")

        magnitude = sum(v**2 for v in value)
        if not (0.999 <= magnitude <= 1.001):  # Allowing some tolerance for floating-point precision
            raise ValueError("relative_direction must be a unit vector (magnitude = 1)")

    
class AngularAcceleration(Element2):
    """
    This joint imposes the absolute angular acceleration of a node about a given axis.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    node_label: Union[int, MBVar]
    relative_direction: List[Union[float, MBVar]]
    acceleration: Union['DriveCaller', 'DriveCaller2']

    def element_type(self):
        return 'joint'
    
    @field_validator('relative_direction')
    def validate_relative_direction(cls, v):
        Element2.check_unit_vector3(v)
        return v
    
    def __str__(self):
        s = f'''{self.element_header()}, angular acceleration'''
        s += f''',\n\t{self.node_label}, {self.relative_direction}'''
        s += f''',\n\t{self.acceleration}'''
        s += self.element_footer()
        return s

class AngularVelocity(Element2):
    """
    Represents a joint imposing the absolute angular velocity of a node about a given axis.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    node_label: Union[int, MBVar]
    relative_direction: List[Union[float, MBVar]]
    velocity: Union['DriveCaller', 'DriveCaller2']

    def element_type(self):
        return 'joint'

    @field_validator('relative_direction')
    def validate_relative_direction(cls, v):
        Element2.check_unit_vector3(v)
        return v
    
    def __str__(self):
        s = f'''{self.element_header()}, angular velocity'''
        s += f''',\n\t{self.node_label}, '''
        s += ', '.join(str(i) for i in self.relative_direction)
        s += f''',\n\t{self.velocity}'''
        s += self.element_footer()
        return s
    
class AxialRotation(Element2):
    """
    This joint is equivalent to a revolute hinge, but the angular velocity about axis 3 is imposed by means of the driver.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    node_1_label: Union[int, MBVar]
    position_1: Position2
    orientation_mat_1: Position2
    node_2_label: Union[int, MBVar]
    position_2: Position2
    orientation_mat_2: Position2
    angular_velocity: Union['DriveCaller', 'DriveCaller2']

    def element_type(self):
        return 'joint'
    
    def __str__(self):
        s = f'{self.element_header()}, axial rotation'
        s += f''',\n\t{self.node_1_label}'''
        s += f''',\n\t\tposition, {self.position_1}'''
        s += f''',\n\t\torientation, {self.orientation_mat_1}'''
        s += f''',\n\t{self.node_2_label}'''
        s += f''',\n\t\tposition, {self.position_2}'''
        s += f''',\n\t\torientation, {self.orientation_mat_2}'''
        s += f''',\n\t{self.angular_velocity}'''
        s += self.element_footer()
        return s

class BeamSlider(Element2):
    """
    This joint implements a slider, e.g. it constrains a structural node on a string of three-node beams.
    """
    model_config = {
        'arbitrary_types_allowed': True  # Allow arbitrary types such as Beam
    }

    slider_node_label: Union[int, MBVar]
    position: Position2
    orientation: Optional[Position2]
    slider_type: Optional[str] = None  # should be one of 'spherical', 'classic', or 'spline'
    beam_number: Union[int, MBVar]
    three_node_beam: 'Beam'
    first_node_offset: Union[str, Position2]
    first_node_orientation: Optional[Union[str, Position2]]
    mid_node_offset: Position2
    mid_node_orientation: Optional[Union[str, Position2]]
    end_node_offset: Position2
    end_node_orientation: Optional[Union[str, Position2]]
    initial_beam: Optional['Beam']
    initial_node: Optional[Union[Node2, Node]]
    smearing_factor: Optional[Union[float, MBVar, int]]

    def element_type(self):
        return 'joint'

    @field_validator('slider_type')
    def validate_slider_type(cls, v):
        allowed_types = {'spherical', 'classic', 'spline'}
        if v is not None and v not in allowed_types:
            raise ValueError(f"slider_type must be one of {allowed_types}")
        return v
    
    def __str__(self):
        s = f'{self.element_header()}, kinematic'
        s += f''',\n\t{self.slider_node_label}'''
        s += f''',\n\t\t{self.position}'''
        if self.orientation is not None:
            s += f''',\n\t\thinge, {self.orientation}'''
        if self.slider_type is not None:
            s += f''',\n\ttype, {self.slider_type}'''
        s += f''',\n\t{self.beam_number}'''
        s += f''',\n\t\t{self.three_node_beam}'''
        if s.endswith(';\n'):
            s = s[:-2] # Remove the last two characters
        if isinstance(self.first_node_offset, str) and self.first_node_offset == 'same':
            s += f''',\n\t\t\tsame'''
        else:
            s += f''',\n\t\t\t{self.first_node_offset}'''
        if self.first_node_orientation is not None:
            s += f''',\n\t\thinge, {self.first_node_orientation}'''
        s += f''',\n\t\t\t{self.mid_node_offset}'''
        if self.mid_node_orientation is not None:
            s += f''',\n\t\thinge, {self.mid_node_orientation}'''
        s += f''',\n\t\t\t{self.end_node_offset}'''
        if self.end_node_orientation is not None:
            s += f''',\n\t\thinge, {self.end_node_orientation}'''
        if self.initial_beam is not None:
            s += f''',\n\tinitial beam, {self.initial_beam}'''
            if s.endswith(';\n'):
                s = s[:-2]  # Remove the last two characters
        if self.initial_node is not None:
            s += f''',\n\tinitial node, {self.initial_node}'''
            if s.endswith(';\n'):
                s = s[:-2]  # Remove the last two characters
        if self.smearing_factor is not None:
            s += f''',\n\tsmearing, {self.smearing_factor}'''
        s += self.element_footer()
        return s

class Brake(Element2):
    """
    This element models a wheel brake, i.e., a constraint that applies a frictional internal torque between two
    nodes about an axis. The frictional torque depends on the normal force that is applied as an external
    input by means of the same friction models implemented for regular joints.
    """
    model_config = {
        'arbitrary_types_allowed': True
    }

    node_1_label: Union[int, MBVar]
    position_1: Position2
    orientation_mat_1: Optional[Position2] = None
    node_2_label: Union[int, MBVar]
    position_2: Position2
    orientation_mat_2: Optional[Position2] = None
    average_radius: Union[float, MBVar]
    preload: Optional[Union[float, MBVar, int]] = None
    friction_model: str  # TODO: Implement FrictionModel class
    shape_function: str  # TODO: Implement ShapeFunction class
    normal_force: Union['DriveCaller', 'DriveCaller2']

    def element_type(self):
        return 'joint'

    def __str__(self):
        s = f'{self.element_header()}, brake'
        s += f''',\n\t{self.node_1_label}, {self.position_1}'''
        if self.orientation_mat_1 is not None:
            s += f''',\n\thinge, {self.orientation_mat_1}'''
        s += f''',\n\t{self.node_2_label}, {self.position_2}'''
        if self.orientation_mat_2 is not None:
            s += f''',\n\thinge, {self.orientation_mat_2}'''
        s += f''',\n\tfriction, {self.average_radius}'''
        if self.preload is not None:
            s += f''',\n\t\tpreload, {self.preload}'''
        s += f''',\n\t\t{self.friction_model}'''
        s += f''',\n\t\t{self.shape_function}'''
        s += f''',\n\t{self.normal_force}'''
        s += self.element_footer()
        return s
    
class CardanoHinge2(Element2):
    '''
    This joint implements a Cardano's joint, also known as Hooke's joint or Universal joint, which is made
    of a sequence of two revolute hinges orthogonal to each other, one about relative axis 2 and one about
    relative axis 3 of the reference systems defined by the two orientation statements. 
    
    In other words, this joint constrains the relative axis 3 of node 1 to be always orthogonal to the 
    relative axis 2 of node 2. As a result, torque is transmitted about axis 1 of both nodes. The relative 
    position is constrained as well.

    Note: This joint does not represent a constant velocity joint, so, when a steady deflection between 
    the two nodes is present, a constant velocity about axis 1 of one node results in an oscillating 
    velocity about axis 1 for the other node.
    '''

    model_config = ConfigDict(arbitrary_types_allowed=True)

    node_1_label: Union[int, MBVar]
    position_1: Position2  # Required according to manual
    orientation_mat_1: Optional[Union[Position2, list]] = None
    node_2_label: Union[int, MBVar]
    position_2: Position2  # Required according to manual
    orientation_mat_2: Optional[Union[Position2, list]] = None

    def element_type(self):
        return 'joint'

    def __str__(self):
        s = f'{self.element_header()}, cardano hinge'
        s += f',\n\t{self.node_1_label}'
        s += f',\n\t\tposition, {self.position_1}'
        if self.orientation_mat_1 is not None:
            s += f',\n\t\torientation, {self.orientation_mat_1}'
        s += f',\n\t{self.node_2_label}'
        s += f',\n\t\tposition, {self.position_2}'
        if self.orientation_mat_2 is not None:
            s += f',\n\t\torientation, {self.orientation_mat_2}'
        s += self.element_footer()
        return s
    
class CardanoPin(Element2):
    """
    This joint implements a 'Cardano' joint between a node and the ground.
    The absolute position is also constrained.
    """

    node_label: Union[int, MBVar]
    position: Position2
    orientation_mat: Optional[Position2] = None
    absolute_pin_position: Position2
    absolute_pin_orientation_mat: Optional[Position2] = None

    def element_type(self):
        return 'joint'

    def __str__(self):
        s = f'{self.element_header()}, cardano pin'
        s += f',\n\t{self.node_label},'
        s += f'\n\t\tposition, {self.position}'
        if self.orientation_mat is not None:
            s += f',\n\t\torientation, {self.orientation_mat}'
        s += f',\n\tposition, {self.absolute_pin_position}'
        if self.absolute_pin_orientation_mat is not None:
            s += f',\n\torientation, {self.absolute_pin_orientation_mat}'
        s += self.element_footer()
        return s

class CardanoRotation(Element2):
    """
    This joint implements a 'Cardano' joint, which is made of a sequence of two orthogonal revolute hinges.
    The relative position is not constrained.
    """

    node_1_label: Union[int, MBVar]
    orientation_mat_1: Optional[Position2] = None
    node_2_label: Union[int, MBVar]
    orientation_mat_2: Optional[Position2] = None

    def element_type(self):
        return 'joint'

    def __str__(self):
        s = f'{self.element_header()}, cardano rotation'
        s += f',\n\t{self.node_1_label}'
        if self.orientation_mat_1 is not None:
            s += f',\n\t\torientation, {self.orientation_mat_1}'
        s += f',\n\t{self.node_2_label}'
        if self.orientation_mat_2 is not None:
            s += f',\n\t\torientation, {self.orientation_mat_2}'
        s += self.element_footer()
        return s

class DeformableAxial(Element2):
    """
    This joint implements a configuration dependent moment that is exchanged between two nodes about
    an axis rigidly attached to the first node. 
    """
    model_config = {
        'arbitrary_types_allowed': True
    }

    node_1_label: Union[int, MBVar]
    position_1: Optional[Position2] = None
    orientation_mat_1: Optional[Position2] = None
    node_2_label: Union[int, MBVar]
    position_2: Optional[Position2] = None
    orientation_mat_2: Optional[Position2] = None
    const_law: Union['ConstitutiveLaw', 'NamedConstitutiveLaw']

    def element_type(self):
        return 'joint'

    def __str__(self):
        s = f'{self.element_header()}, deformable axial'
        s += f',\n\t{self.node_1_label}'
        if self.position_1 is not None:
            s += f',\n\t\tposition, {self.position_1}'
        if self.orientation_mat_1 is not None:
            s += f',\n\t\torientation, {self.orientation_mat_1}'
        s += f',\n\t{self.node_2_label}'
        if self.position_2 is not None:
            s += f',\n\t\tposition, {self.position_2}'
        if self.orientation_mat_2 is not None:
            s += f',\n\t\torientation, {self.orientation_mat_2}'
        s += f',\n\t{self.const_law}'
        s += self.element_footer()
        return s
    
class DeformableHinge2(Element2):
    """
    This joint implements a configuration dependent moment that is exchanged between two nodes. The
    moment may depend, by way of a generic 3D constitutive law, on the relative orientation and angular
    velocity of the two nodes, expressed in the reference frame of node 1.
    """
    model_config = {
        'arbitrary_types_allowed': True
    }

    node_1_label: Union[int, MBVar]
    position_1: Optional[Position2] = None
    orientation_mat_1: Optional[Position2] = None
    node_2_label: Union[int, MBVar]
    position_2: Optional[Position2] = None
    orientation_mat_2: Optional[Position2] = None
    const_law: Union['ConstitutiveLaw', 'NamedConstitutiveLaw']

    def element_type(self):
        return 'joint'
    
    def __str__(self):
        s = f'{self.element_header()}, deformable hinge'
        s += f',\n\t{self.node_1_label}'
        if self.position_1 is not None:
            s += f',\n\t\tposition, {self.position_1}'
        if self.orientation_mat_1 is not None:
            s += f',\n\t\torientation, {self.orientation_mat_1}'
        s += f',\n\t{self.node_2_label}'
        if self.position_2 is not None:
            s += f',\n\t\tposition, {self.position_2}'
        if self.orientation_mat_2 is not None:
            s += f',\n\t\torientation, {self.orientation_mat_2}'
        s += f',\n\t{self.const_law}'
        s += self.element_footer()
        return s

class Distance(Element2):
    """
    This joint forces the distance between two points, each relative to a node, to assume the value indicated
    by the drive. If no offset is given, the points are coincident with the node themselves.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    node_1_label: Union[int, MBVar]
    position_1: Optional[Position2] = None
    node_2_label: Union[int, MBVar]
    position_2: Optional[Position2] = None
    distance: Union['DriveCaller', 'DriveCaller2', str]

    @field_validator('distance')
    def validate_distance(cls, value):
        if isinstance(value, str):
            if value != "from nodes":
                raise ValueError('Invalid value for distance. It must be "from nodes" if a string.')
        return value
    
    def element_type(self):
        return 'joint'
    
    def __str__(self):
        s = f'{self.element_header()}, distance'
        s += f''',\n\t{self.node_1_label}'''
        if self.position_1 is not None:
            s += f''', position, {self.position_1}'''
        s += f''',\n\t{self.node_2_label}'''
        if self.position_2 is not None:
            s += f''', position, {self.position_2}'''
        s += f''',\n\t{self.distance}'''
        s += self.element_footer()
        return s

class DriveDisplacement(Element2):
    '''
    This joint imposes the relative position between two points optionally offset from two structural nodes,
    in the form of a vector that expresses the direction of the displacement in the reference frame of node 1,
    whose amplitude is defined by a drive.
    '''
    model_config = ConfigDict(arbitrary_types_allowed=True)


    node_1_label: Union[int, MBVar]
    position_1: Position2
    node_2_label: Union[int, MBVar]
    position_2: Position2
    relative_position: 'TplDriveCaller'

    def element_type(self):
        return 'joint'

    def __str__(self):
        s = f'{self.element_header()}, drive displacement'
        s += f''',\n\t{self.node_1_label}, {self.position_1}'''
        s += f''',\n\t{self.node_2_label}, {self.position_2}'''
        s += f''',\n\t{self.relative_position}'''
        s += self.element_footer()
        return s
    
class DriveDisplacementPin(Element2):
    '''
    This joint imposes the relative position between two points optionally offset from two structural nodes,
    in the form of a vector that expresses the direction of the displacement in the reference frame of node 1,
    whose amplitude is defined by a drive.
    '''
    model_config = ConfigDict(arbitrary_types_allowed=True)

    node_label: Union[int, MBVar]
    node_offset: Position2
    offset: Position2
    position: 'TplDriveCaller'

    def element_type(self):
        return 'joint'

    def __str__(self):
        s = f'{self.element_header()}, drive displacement pin'
        s += f''',\n\t{self.node_label}, {self.node_offset}'''
        s += f''',\n\t{self.offset}'''
        s += f''',\n\t{self.position}'''
        s += self.element_footer()
        return s

class DriveHinge(Element2):
    '''
    This joint imposes the relative orientation between two nodes, in the form of a rotation about an axis
    whose amplitude is defined by a drive.
    '''
    model_config = ConfigDict(arbitrary_types_allowed=True)

    node_1_label: Union[int, MBVar]
    relative_orientation_mat_1: Optional[Position2]
    node_2_label: Union[int, MBVar]
    relative_orientation_mat_2: Optional[Position2]
    hinge_orientation: 'TplDriveCaller'

    def element_type(self):
        return 'joint'

    def __str__(self):
        s = f'{self.element_header()}, drive hinge'
        s += f''',\n\t{self.node_1_label}'''
        if self.relative_orientation_mat_1 is not None:
            s += f''', orientation, {self.relative_orientation_mat_1}'''
        s += f''',\n\t{self.node_2_label}'''
        if self.relative_orientation_mat_2 is not None:
            s += f''', orientation, {self.relative_orientation_mat_2}'''
        s += f''',\n\t{self.hinge_orientation}'''
        s += self.element_footer()
        return s
    
class GimbalRotation(Element2):
    '''
    A homokinetic joint without position constraints; this joint, in conjunction with a spherical hinge 
    joint, should be used to implement an ideal tiltrotor gimbal instead of a cardano
    rotation. It is equivalent to a series of two Cardano's joints (the cardano hinge) rotated 90 degrees
    apart, each accounting for half the relative rotation between axis 3 of each side of the joint.
    '''

    node_1_label: Union[int, MBVar]
    relative_orientation_mat_1: Optional[Union[Position2, List]] = None
    node_2_label: Union[int, MBVar]
    relative_orientation_mat_2: Optional[Union[Position2, List]] = None
    orientation_description: Optional[str] = None
    """The type of orientation description"""

    @field_validator('orientation_description')
    def check_orientation_description(cls, v):
        if v is None:
            return v  # Field is optional and not provided; no validation needed
        allowed_values = {"euler123", "euler313", "euler321", "orientation vector", "orientation matrix"}
        if v not in allowed_values:
            raise ValueError(f"Invalid orientation description. Must be one of: {', '.join(allowed_values)}")
        return v

    def element_type(self):
        return 'joint'
    
    def __str__(self):
        s = f'{self.element_header()}, gimbal rotation'
        s += f''',\n\t{self.node_1_label}'''
        if self.relative_orientation_mat_1 is not None:
            s += f''', orientation, {self.relative_orientation_mat_1}'''
        s += f''',\n\t{self.node_2_label}'''
        if self.relative_orientation_mat_2 is not None:
            s += f''', orientation, {self.relative_orientation_mat_2}'''
        if self.orientation_description is not None:
            s += f''',\n\torientation description, {self.orientation_description}'''
        s += self.element_footer()
        return s

class ImposedDisplacement(Element2):
    '''
    This joint imposes the relative position between two points, optionally offset from two structural nodes,
    along a given direction that is rigidly attached to the first node. The amplitude of the displacement is
    defined by a drive.
    '''
    model_config = ConfigDict(arbitrary_types_allowed=True)

    node_1_label: Union[int, MBVar]
    position_1: Position2
    node_2_label: Union[int, MBVar]
    position_2: Position2
    direction: List[Union[float, MBVar]]
    relative_position: Union['DriveCaller', 'DriveCaller2']

    @field_validator('direction')
    def validate_direction(cls, v):
        Element2.check_unit_vector3(v)
        return v

    def element_type(self):
        return 'joint'

    def __str__(self):
        s = f'{self.element_header()}, imposed displacement'
        s += f''',\n\t{self.node_1_label}, {self.position_1}'''
        s += f''',\n\t{self.node_2_label}, {self.position_2}'''
        s += f''',\n\t{self.direction}'''
        s += f''',\n\t{self.relative_position}'''
        s += self.element_footer()
        return s

class ImposedDisplacementPin(Element2):
    '''
    This joint imposes the absolute displacement of a point optionally offset from a structural node, along
    a direction defined in the absolute reference frame. The amplitude of the displacement is defined by a
    drive.
    '''
    model_config = ConfigDict(arbitrary_types_allowed=True)

    node_label: Union[int, MBVar]
    node_offset: Position2
    offset: Position2
    direction: List[Union[float, MBVar]]
    position: Union['DriveCaller', 'DriveCaller2']

    @field_validator('direction')
    def validate_direction(cls, v):
        Element2.check_unit_vector3(v)
        return v

    def element_type(self):
        return 'joint'

    def __str__(self):
        s = f'{self.element_header()}, imposed displacement pin'
        s += f''',\n\t{self.node_label}, {self.node_offset}'''
        s += f''',\n\t{self.offset}'''
        s += f''',\n\t{self.direction}'''
        if self.position.idx is not None and self.position.idx >= 0:
            s += f''',\n\treference, {self.position.idx}'''
        else:
            s += f''',\n\t{self.position}'''
        s += self.element_footer()
        return s
    
class InLine(Element2):
    '''
    This joint forces a point relative to the second node to move along a line attached to the first node.
    '''
    
    node_1_label: Union[int, MBVar]
    position: Optional[Position2] = None
    orientation: Optional[Union[Position2, List]] = None
    node_2_label: Union[int, MBVar]
    offset: Optional[Position2] = None

    def element_type(self):
        return 'joint'

    def __str__(self):
        s = f'{self.element_header()}, in line'
        s += f''',\n\t{self.node_1_label}'''
        if self.position is not None:
            s += f''', position, {self.position}'''
        if self.orientation is not None:
            s += f'''\n\t, orientation, {self.orientation}'''
        s += f''',\n\t{self.node_2_label}'''
        if self.offset is not None:
            s += f''', offset, {self.offset}'''
        s += self.element_footer()
        return s
    
class InPlane(Element2):
    '''
    This joint forces a point relative to the second node to move in a plane attached to the first node.
    '''
    
    node_1_label: Union[int, MBVar]
    position: Optional[Position2] = None
    relative_direction: List[Union[float, MBVar]]
    node_2_label: Union[int, MBVar]
    offset: Optional[Position2] = None

    @field_validator('relative_direction')
    def validate_relative_direction(cls, v):
        Element2.check_unit_vector3(v)
        return v

    def element_type(self):
        return 'joint'

    def __str__(self):
        s = f'{self.element_header()}, in plane'
        s += f''',\n\t{self.node_1_label}'''
        if self.position is not None:
            s += f''', position, {self.position}'''
        s += f''',\n\t{self.relative_direction}'''
        s += f''',\n\t{self.node_2_label}'''
        if self.offset is not None:
            s += f''', offset, {self.offset}'''
        s += self.element_footer()
        return s
    
class LinearAcceleration(Element2):
    '''
    This joint imposes the absolute linear acceleration of a node along a given axis.
    '''
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    node_label: Union[int, MBVar]
    relative_direction: List[Union[float, MBVar]]
    acceleration: Union['DriveCaller', 'DriveCaller2']

    @field_validator('relative_direction')
    def validate_relative_direction(cls, v):
        Element2.check_unit_vector3(v)
        return v

    def element_type(self):
        return 'joint'

    def __str__(self):
        s = f'{self.element_header()}, linear acceleration'
        s += f''',\n\t{self.node_label}'''
        s += f''',\n\t {self.relative_direction}'''
        if self.acceleration.idx is not None and self.acceleration.idx >= 0:
            s += f''',\n\treference, {self.acceleration.idx}'''
        else:
            s += f''',\n\t{self.acceleration}'''
        s += self.element_footer()
        return s
    
class LinearVelocity(Element2):
    '''
    This joint imposes the absolute linear velocity of a node along a given axis.
    '''
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    node_label: Union[int, MBVar]
    relative_direction: List[Union[float, MBVar]]
    velocity: Union['DriveCaller', 'DriveCaller2']

    @field_validator('relative_direction')
    def validate_relative_direction(cls, v):
        Element2.check_unit_vector3(v)
        return v

    def element_type(self):
        return 'joint'

    def __str__(self):
        s = f'{self.element_header()}, linear velocity'
        s += f''',\n\t{self.node_label}'''
        s += f''',\n\t {self.relative_direction}'''
        if self.velocity.idx is not None and self.velocity.idx >= 0:
            s += f''',\n\treference, {self.velocity.idx}'''
        else:
            s += f''',\n\t{self.velocity}'''
        s += self.element_footer()
        return s
    
class Modal(Element2):
    pass

class PlaneDisplacement(Element2):
    '''
    This joint allows two nodes to move in the common relative 1–2 plane and to rotate about the common
    relative axis 3.
    '''

    node_1_label: Union[int, MBVar]
    position_1: Position2
    orientation_mat_1: Optional[Union[Position2, List]] = None
    node_2_label: Union[int, MBVar]
    position_2: Position2
    orientation_mat_2: Optional[Union[Position2, List]] = None

    def element_type(self):
        return 'joint'
    
    def __str__(self):
        s = f'{self.element_header()}, plane displacement'
        s += f''',\n\t{self.node_1_label}, position, {self.position_1}'''
        if self.orientation_mat_1 is not None:
            s += f''',\n\torientation, {self.orientation_mat_1}'''
        s += f''',\n\t{self.node_2_label}, position, {self.position_2}'''
        if self.orientation_mat_2 is not None:
            s += f''',\n\torientation, {self.orientation_mat_2}'''
        s += self.element_footer()
        return s
    
class PlaneDisplacementPin(Element2):
    '''
    This joint allows a node to move in the relative 1–2 plane and to rotate about the relative axis 3 with
    respect to an absolute point and plane.
    '''

    node_label: Union[int, MBVar]
    relative_offset: Position2
    relative_orientation_mat: Optional[Union[Position2, List]] = None
    absolute_pin_position: Position2
    absolute_pin_orientation_mat: Optional[Union[Position2, List]] = None

    def element_type(self):
        return 'joint'
    
    def __str__(self):
        s = f'{self.element_header()}, plane displacement pin'
        s += f''',\n\t{self.node_label}'''
        s += f''',\n\t\tposition, {self.relative_offset}'''
        if self.relative_orientation_mat is not None:
            s += f''',\n\t\torientation, {self.relative_orientation_mat}'''
        s += f''',\n\tposition, {self.absolute_pin_position}'''
        if self.absolute_pin_orientation_mat is not None:
            s += f''',\n\torientation, {self.absolute_pin_orientation_mat}'''
        s += self.element_footer()
        return s

class Prismatic(Element2):
    '''
    This joints constrains the relative orientation of two nodes, so that their orientations remain parallel.
    The relative position is not constrained. The initial orientation of the joint must be compatible: use the
    orientation keyword to assign the joint initial orientation.
    '''

    node_1_label: Union[int, MBVar]
    relative_orientation_mat_1: Optional[Union[Position2, List]] = None
    node_2_label: Union[int, MBVar]
    relative_orientation_mat_2: Optional[Union[Position2, List]] = None

    def element_type(self):
        return 'joint'
    
    def __str__(self):
        s = f'{self.element_header()}, prismatic'
        s += f''',\n\t{self.node_1_label}'''
        if self.relative_orientation_mat_1 is not None:
            s += f''', orientation, {self.relative_orientation_mat_1}'''
        s += f''',\n\t{self.node_2_label}'''
        if self.relative_orientation_mat_2 is not None:
            s += f''', orientation, {self.relative_orientation_mat_2}'''
        s += self.element_footer()
        return s

class RevoluteHinge(Element2):
    '''
    This joint only allows the relative rotation of two nodes about a given axis, which is axis 3 in the reference
    systems defined by the two orientation statements.
    '''

    node_1_label: Union[int, MBVar]
    position_1: Position2
    orientation_mat_1: Optional[Position2] = None
    node_2_label: Union[int, MBVar]
    position_2: Position2
    orientation_mat_2: Optional[Position2] = None
    initial_theta: Optional[Union[float, MBVar]] = None
    friction: Optional[Union[float, MBVar]] = None
    preload: Optional[Union[float, MBVar]] = None
    friction_model: Optional[str] = None # TODO: Define FrictionModel
    shape_function: Optional[str] = None # TODO: Define ShapeFunction

    def element_type(self):
        return 'joint'
    
    @model_validator(mode='after')
    def check_friction_parameters(self):
        if self.friction is not None:
            if self.friction_model is None or self.shape_function is None:
                raise ValueError("When 'friction' is specified, 'friction_model' and 'shape_function' must also be specified.")
            # 'preload' is optional when 'friction' is specified
        else:
            # If 'friction' is not specified, none of the friction-related parameters should be specified
            if any(param is not None for param in [self.preload, self.friction_model, self.shape_function]):
                raise ValueError("If 'friction' is not specified, 'preload', 'friction_model', and 'shape_function' should not be specified.")
        return self

    def __str__(self):
        s = f'{self.element_header()}, revolute hinge'
        s += f',\n\t{self.node_1_label}'
        s += f',\n\t\tposition, {self.position_1}'
        if self.orientation_mat_1 is not None:
            s += f',\n\t\torientation, {self.orientation_mat_1}'
        s += f',\n\t{self.node_2_label}'
        s += f',\n\t\tposition, {self.position_2}'
        if self.orientation_mat_2 is not None:
            s += f',\n\t\torientation, {self.orientation_mat_2}'
        if self.initial_theta is not None:
            s += f',\n\tinitial theta, {self.initial_theta}'
        if self.friction is not None:
            s += f',\n\tfriction, {self.friction}'
            if self.preload is not None:
                s += f',\n\t\tpreload, {self.preload}'
            s += f',\n\t\t{self.friction_model}'
            s += f',\n\t\t{self.shape_function}'
        s += self.element_footer()
        return s

class RevolutePin(Element2):
    """
    This joint only allows the absolute rotation of a node about a given axis, which is axis 3 in the reference
    systems defined by the two orientation statements.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    node_label: Union[int, MBVar]
    relative_offset: Position2
    relative_orientation_mat: Optional[Union[Position2, list]] = None
    absolute_pin_position: Position2
    absolute_pin_orientation_mat: Optional[Union[Position2, list]] = None
    initial_theta: Optional[Union[float, MBVar, expression]] = None

    def element_type(self):
        return 'joint'

    def __str__(self):
        s = f'{self.element_header()}, revolute pin'
        s += f',\n\t{self.node_label}'
        s += f',\n\t\tposition, {self.relative_offset}'
        if self.relative_orientation_mat is not None:
            s += f',\n\t\torientation, {self.relative_orientation_mat}'
        s += f',\n\tposition, {self.absolute_pin_position}'
        if self.absolute_pin_orientation_mat is not None:
            s += f',\n\torientation, {self.absolute_pin_orientation_mat}'
        if self.initial_theta is not None:
            s += f',\n\tinitial theta, {self.initial_theta}'
        s += self.element_footer()
        return s
    
class RevoluteRotation(Element2):
    '''
    This joint allows the relative rotation of two nodes about a given axis, which is axis 3 in the reference
    systems defined by the two orientation statements. The relative position is not constrained.
    '''

    node_1_label: Union[int, MBVar]
    position_1: Optional[Position2] = None
    orientation_mat_1: Optional[Union[Position2, list]] = None
    node_2_label: Union[int, MBVar]
    position_2: Optional[Position2] = None
    orientation_mat_2: Optional[Union[Position2, list]] = None

    def element_type(self):
        return 'joint'

    def __str__(self):
        s = f'{self.element_header()}, revolute rotation'
        s += f',\n\t{self.node_1_label}'
        if self.position_1 is not None:
            s += f',\n\t\tposition, {self.position_1}'
        if self.orientation_mat_1 is not None:
            s += f',\n\t\torientation, {self.orientation_mat_1}'
        s += f',\n\t{self.node_2_label}'
        if self.position_2 is not None:
            s += f',\n\t\tposition, {self.position_2}'
        if self.orientation_mat_2 is not None:
            s += f',\n\t\torientation, {self.orientation_mat_2}'
        s += self.element_footer()
        return s

# Rename to Rod, Delete current Rod, when review of the code is done
class Rod2(Element2):
    '''
    The rod element represents a force between two nodes that depends on the relative position and velocity
    of two points, each rigidly attached to a structural node. The direction of the force is also based on
    the relative position of the points: it is the line that passes through them. If no offset is defined, the
    points are the nodes themselves.
    '''
    model_config = {
        'arbitrary_types_allowed': True
    }

    node_1_label: Union[int, MBVar]
    position_1: Optional[Position2] = None
    node_2_label: Union[int, MBVar]
    position_2: Optional[Position2] = None
    rod_length: Union[float, MBVar, str]  # Can be a float or 'from nodes'
    const_law: Union['ConstitutiveLaw', 'NamedConstitutiveLaw']

    def element_type(self):
        return 'joint'
    
    @field_validator('rod_length')
    def validate_rod_length(cls, v):
        if isinstance(v, str):
            if v.lower() != 'from nodes':
                raise ValueError("rod_length must be a float, MBVar or the string 'from nodes'")
            return v.lower()
        else:
            return v
    
    @field_validator('const_law')
    def validate_const_law(cls, v):
        if isinstance(v, ConstitutiveLaw):
            if v.law_type != ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW:
                raise ValueError("const_law must be a 1D constitutive law with law_type 'SCALAR_ISOTROPIC_LAW'")
            return v
        elif isinstance(v, NamedConstitutiveLaw):
            return v
        else:
            raise TypeError("const_law must be an instance of ConstitutiveLaw or NamedConstitutiveLaw")

    def __str__(self):
        s = f'{self.element_header()}, rod'
        s += f',\n\t{self.node_1_label}'
        if self.position_1 is not None:
            s += f',\n\t\tposition, {self.position_1}'
        s += f',\n\t{self.node_2_label}'
        if self.position_2 is not None:
            s += f',\n\t\tposition, {self.position_2}'
        s += f',\n\t{self.rod_length}'
        s += f',\n\t{self.const_law}'
        s += self.element_footer()
        return s
    
class RodWithOffset(Element2):
    '''
    Analogous to the rod joint with the optional offsets.
    '''
    model_config = {
        'arbitrary_types_allowed': True
    }

    node_1_label: Union[int, MBVar]
    position_1: Position2  # Required
    node_2_label: Union[int, MBVar]
    position_2: Position2  # Required
    rod_length: Union[float, MBVar, str]  # Can be a float, MBVar or 'from nodes'
    const_law: Union['ConstitutiveLaw', 'NamedConstitutiveLaw']  # Should be a 1D constitutive law

    def element_type(self):
        return 'joint'

    @field_validator('rod_length')
    def validate_rod_length(cls, v):
        if isinstance(v, str):
            if v.lower() != 'from nodes':
                raise ValueError("rod_length must be a float or the string 'from nodes'")
            return v.lower()
        else:
            return v

    @field_validator('const_law')
    def validate_const_law(cls, v):
        if isinstance(v, ConstitutiveLaw):
            if v.law_type != ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW:
                raise ValueError("const_law must be a 1D constitutive law with law_type 'SCALAR_ISOTROPIC_LAW'")
            return v
        elif isinstance(v, NamedConstitutiveLaw):
            return v
        else:
            raise TypeError("const_law must be an instance of ConstitutiveLaw or NamedConstitutiveLaw")

    def __str__(self):
        s = f'{self.element_header()}, rod with offset'
        s += f',\n\t{self.node_1_label}'
        s += f',\n\t\t{self.position_1}'
        s += f',\n\t{self.node_2_label}'
        s += f',\n\t\t{self.position_2}'
        if isinstance(self.rod_length, str) and self.rod_length == 'from nodes':
            s += f',\n\tfrom nodes'
        else:
            s += f',\n\t{self.rod_length}'
        s += f',\n\t{self.const_law}'
        s += self.element_footer()
        return s

class RodBezier(Element2):
    '''
    This joint, in analogy with the rod joint, represents a force that acts between two points each rigidly
    attached to a structural node.

    The force on node 1 acts along the line connecting the insertion point, defined in the reference frame of
    the node by <relative_offset_1> and a first intermediate point defined, also in the reference frame of
    the node, by <relative_offset_2>. In the same way, the force on node 2 is applied at the insertion
    point of the element, defined in the reference frame of node 2 by <relative_offset_4> and acts along
    the line connecting a second intermediate point defined by <relative_offset_3>.

    The element internally is represented as a Bézier spline of order 3, which length and instantaneous
    lengthening velocity are calculated using Gauss-Legendre quadrature.

    The absolute value of the force depends on the strain and strain rate of the curve as in the standard rod
    element as determined by the ConstitutiveLaw<1D> <const_law>.
    '''
    model_config = {
        'arbitrary_types_allowed': True
    }

    node_1_label: Union[int, MBVar]
    position_1: Position2
    position_2: Position2
    node_2_label: Union[int, MBVar]
    position_3: Position2
    position_4: Position2
    rod_length: Union[float, MBVar, str]  # Can be a float or 'from nodes'
    const_law: Union['ConstitutiveLaw', 'NamedConstitutiveLaw']  # Should be a 1D constitutive law
    integration_order: int = 2  # Defaults to 2
    integration_segments: int = 3  # Defaults to 3

    def element_type(self):
        return 'joint'

    @field_validator('rod_length')
    def validate_rod_length(cls, v):
        if isinstance(v, str):
            if v.lower() != 'from nodes':
                raise ValueError("rod_length must be a float or the string 'from nodes'")
            return v.lower()
        else:
            return v

    @field_validator('const_law')
    def validate_const_law(cls, v):
        if isinstance(v, ConstitutiveLaw):
            if v.law_type != ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW:
                raise ValueError("const_law must be a 1D constitutive law with law_type 'SCALAR_ISOTROPIC_LAW'")
            return v
        elif isinstance(v, NamedConstitutiveLaw):
            return v
        else:
            raise TypeError("const_law must be an instance of ConstitutiveLaw or NamedConstitutiveLaw")

    @field_validator('integration_order')
    def validate_integration_order(cls, v):
        if not isinstance(v, int):
            raise TypeError("integration_order must be an integer")
        if not (1 <= v <= 10):
            raise ValueError("integration_order must be between 1 and 10")
        return v

    @field_validator('integration_segments')
    def validate_integration_segments(cls, v):
        if not isinstance(v, int):
            raise TypeError("integration_segments must be an integer")
        if v <= 0:
            raise ValueError("integration_segments must be a positive integer")
        return v

    def __str__(self):
        s = f'{self.element_header()}, rod bezier'
        s += f',\n\t{self.node_1_label}'
        s += f',\n\t\t{self.position_1}'
        s += f',\n\t\t{self.position_2}'
        s += f',\n\t{self.node_2_label}'
        s += f',\n\t\t{self.position_3}'
        s += f',\n\t\t{self.position_4}'
        if isinstance(self.rod_length, str) and self.rod_length == 'from nodes':
            s += f',\n\tfrom nodes'
        else:
            s += f',\n\t{self.rod_length}'
        # Include integration order only if it differs from the default value of 2
        if self.integration_order != 2:
            s += f',\n\tintegration order, {self.integration_order}'
        # Include integration segments only if it differs from the default value of 3
        if self.integration_segments != 3:
            s += f',\n\tintegration segments, {self.integration_segments}'
        s += f',\n\t{self.const_law}'
        s += self.element_footer()
        return s
    
class SphericalHinge2(Element2):
    '''
    This joint constrains the relative position of two nodes; the relative orientation is not constrained.

    The joint is defined by two nodes and optional position and orientation offsets. The positions are defined
    by the `position` keyword and the orientations by the `orientation` keyword. If not specified, default
    values are assumed (zero offset for position and identity matrix for orientation).

    Note: The orientation matrices are used for output purposes only.
    '''

    model_config = ConfigDict(arbitrary_types_allowed=True)

    node_1_label: Union[int, MBVar]
    position_1: Optional[Position2] = None
    orientation_mat_1: Optional[Union[Position2, list]] = None
    node_2_label: Union[int, MBVar]
    position_2: Optional[Position2] = None
    orientation_mat_2: Optional[Union[Position2, list]] = None

    def element_type(self):
        return 'joint'

    def __str__(self):
        s = f'{self.element_header()}, spherical hinge'
        s += f',\n\t{self.node_1_label}'
        if self.position_1 is not None:
            s += f',\n\t\tposition, {self.position_1}'
        if self.orientation_mat_1 is not None:
            s += f',\n\t\torientation, {self.orientation_mat_1}'
        s += f',\n\t{self.node_2_label}'
        if self.position_2 is not None:
            s += f',\n\t\tposition, {self.position_2}'
        if self.orientation_mat_2 is not None:
            s += f',\n\t\torientation, {self.orientation_mat_2}'
        s += self.element_footer()
        return s

class SphericalPin(Element2):
    '''
    This joint constrains the absolute position of a node; the relative orientation is not constrained.
    **Note**: This joint is equivalent to a spherical hinge when one node is grounded.
    '''

    node_label: Union[int, 'MBVar']
    position: Optional[Position2] = None
    orientation_mat: Optional[Union[Position2, list]] = None
    absolute_pin_position: Position2
    absolute_orientation_mat: Optional[Union[Position2]] = None

    def element_type(self):
        return 'joint'

    def __str__(self):
        s = f'{self.element_header()}, spherical pin'
        s += f',\n\t{self.node_label}'
        if self.position is not None:
            s += f',\n\t\tposition, {self.position}'
        if self.orientation_mat is not None:
            s += f',\n\t\torientation, {self.orientation_mat}'
        s += f',\n\tposition, {self.absolute_pin_position}'
        if self.absolute_orientation_mat is not None:
            s += f',\n\torientation, {self.absolute_orientation_mat}'
        s += self.element_footer()
        return s
    
class ViscousBody(Element2):
    '''
    This element defines a force and a moment that depend on the absolute linear and angular velocity of
    a body, projected in the reference frame of the node itself. The force and moment are defined as a 6D
    viscous constitutive law.
    '''
    model_config = {
        'arbitrary_types_allowed': True
    }

    node_label: Union[int, MBVar]
    position: Optional[Position2] = None
    orientation_mat: Optional[Union[Position2, list]] = None
    const_law: Union['ConstitutiveLaw','NamedConstitutiveLaw']  # Should be a 6D constitutive law

    def element_type(self):
        return 'joint'
    
    @field_validator('const_law')
    def validate_const_law(cls, v):
        if isinstance(v, ConstitutiveLaw):
            if v.law_type != ConstitutiveLaw.LawType.D6_ISOTROPIC_LAW:
                raise ValueError("const_law must be a 6D constitutive law with law_type 'D6_ISOTROPIC_LAW'")
            return v
        elif isinstance(v, NamedConstitutiveLaw):
            return v
        else:
            raise TypeError("const_law must be an instance of ConstitutiveLaw or NamedConstitutiveLaw")
    
    def __str__(self):
        s = f'{self.element_header()}, viscous body'
        s += f',\n\t{self.node_label}'
        if self.position is not None:
            s += f',\n\t\tposition, {self.position}'
        if self.orientation_mat is not None:
            s += f',\n\t\torientation, {self.orientation_mat}'
        s += f',\n\t{self.const_law}'
        s += self.element_footer()
        return s
    
class Body(Element):
    def __init__(self, idx, node, mass, position, inertial_matrix, inertial = null,
            output = 'yes'):
        assert isinstance(position, Position), (
            '\n-------------------\nERROR:' +
            ' in defining a body, the center of mass relative position ' + 
            ' mass must be an instance of the Position class;' + 
            '\n-------------------\n')
        assert isinstance(inertial_matrix, list), (
            '\n-------------------\nERROR:' + 
            ' in defining a body, the inertial matrix' + 
            ' must be a list;' + 
            '\n-------------------\n')
        self.idx = idx
        self.type = 'body'
        self.node = node
        self.mass = mass
        self.position = position
        self.inertial_matrix = inertial_matrix
        self.inertial = inertial
        self.output = output
    def __str__(self):
        s = 'body: ' + str(self.idx) + ', ' + str(self.node) + ',\n'
        s = s + '\t' + str(self.mass) + ',\n'
        s = s + '\t' + str(self.position) + ',\n'
        s = s + '\t' + ', '.join(str(i) for i in self.inertial_matrix) 
        if self.inertial != null:
            s = s + ',\n'
            if isinstance(self.inertial, list):
                s = s + ', '.join(str(i) for i in self.inertial)
            else:
                s = s + ', ' + self.inertial
        if self.output != 'yes':
            s = s + ',\n\toutput, ' + str(self.output)
        s = s + ';\n'
        return s

class StructuralForce(Element):
    def __init__(self, idx, node, ftype, position, force_drive, 
            force_orientation = [], moment_orientation = [],
            moment_drive = [], output = 'yes'):
        assert isinstance(position, Position), (
            '\n-------------------\nERROR:' + 
            ' in defining a structural force, the relative arm must be' +
            ' an instance of the Position class;' + 
            '\n-------------------\n')
        assert ftype in {'absolute', 'follower', 'total'}, (
            '\n-------------------\nERROR:' + 
            ' unrecognised type of structural force: ' + str(ftype) + 
            '\n-------------------\n')
        if ftype == 'total':
            assert isinstance(force_orientation, Position), (
                '\n-------------------\nERROR:' + 
                ' in defining a structural total force, the force orientation ' +
                ' must be an instance of the Position class;' + 
                '\n-------------------\n')
            assert isinstance(moment_orientation, Position), (
                '\n-------------------\nERROR:' + 
                ' in defining a structural total force, the moment orientation ' +
                ' must be an instance of the Position class;' + 
                '\n-------------------\n')
        self.idx = idx
        self.type = 'force'
        self.node = node
        self.ftype = ftype
        self.position = position
        self.force_drive = force_drive
        self.force_orientation = force_orientation
        self.moment_orientation = moment_orientation
        self.moment_drive = moment_drive
        self.output = output
    def __str__(self):
        s = 'force: ' + str(self.idx) + ', ' + self.ftype
        s = s + ',\n\t' + str(self.node)
        s = s + ',\n\t\tposition, ' + str(self.position)
        if self.ftype == 'total':
            s = s + ',\n\t\tforce orientation, ' + str(self.force_orientation)
            s = s + ',\n\t\tmoment orientation, ' + str(self.moment_orientation)
            s = s + ',\n\t\tforce, ' + ', '.join(str(i) for i in self.force_drive)
            s = s + ',\n\t\tmoment, ' + ', '.join(str(i) for i in self.moment_drive)
        else: # ftype = { absolute|follower }
            s = s + ',\n\t\t' + ', '.join(str(i) for i in self.force_drive)
        if self.output != 'yes':
            s = s + ',\n\toutput, ' + str(self.output)
        s = s + ';\n'
        return s


class StructuralInternalForce(Element):
    def __init__(self, idx, nodes, ftype, positions, force_drive, 
            force_orientation = [], moment_orientation = [],
            moment_drive = [], output = 'yes'):
        assert len(nodes) == 2, (
            '\n-------------------\nERROR:' + 
            ' defining a structural internal force with ' + str(len(nodes)) +
            ' nodes' + '\n-------------------\n')
        assert all(isinstance(pos, Position) for pos in positions) , (
            '\n-------------------\nERROR:' + 
            ' in defining a structural internal force all relative arms ' +
            ' must be instances of the Position class;' + 
            '\n-------------------\n')
        assert ftype in {'absolute', 'follower', 'total'}, (
            '\n-------------------\nERROR:' + 
            ' unrecognised type of structural internal force: ' + str(ftype) + 
            '\n-------------------\n')
        if ftype == 'total':
            assert all(isinstance(pos, Position) for pos in force_orientation), (
                '\n-------------------\nERROR:' + 
                ' in defining a structural total internal force all the ' +
                ' force orientations must be instances of the Position class;' + 
                '\n-------------------\n')
            assert all(isinstance(pos, Position) for pos in moment_orientation), (
                '\n-------------------\nERROR:' + 
                ' in defining a structural total internal force all the ' +
                ' moment orientations must be instances of the Position class;' + 
                '\n-------------------\n')
        self.idx = idx
        self.type = 'force'
        self.nodes = nodes
        self.ftype = ftype
        self.positions = positions
        self.force_drive = force_drive
        self.force_orientation = force_orientation
        self.moment_orientation = moment_orientation
        self.moment_drive = moment_drive
        self.output = output
    def __str__(self):
        s = 'force: ' + str(self.idx) + ', ' + self.ftype + ' internal'
        s = s + ',\n\t' + str(self.nodes[0])
        s = s + ',\n\t\tposition, ' + str(self.positions[0])
        if self.ftype == 'total':
            s = s + ',\n\t\tforce orientation, ' + str(self.force_orientation[0])
            s = s + ',\n\t\tmoment orientation, ' + str(self.moment_orientation[0])
        s = s + ',\n\t' + str(self.nodes[1])
        s = s + ',\n\t\tposition, ' + str(self.positions[1])
        if self.ftype == 'total':
            s = s + ',\n\t\tforce orientation, ' + str(self.force_orientation[1])
            s = s + ',\n\t\tmoment orientation, ' + str(self.moment_orientation[1])
            s = s + ',\n\t\tforce, ' + ', '.join(str(i) for i in self.force_drive)
            s = s + ',\n\t\tmoment, ' + ', '.join(str(i) for i in self.moment_drive)
        else: # ftype = { absolute|follower }
            s = s + ',\n\t\t' + ', '.join(str(i) for i in self.force_drive)
        if self.output != 'yes':
            s = s + ',\n\toutput, ' + str(self.output)
        s = s + ';\n'
        return s


class StructuralCouple(Element):
    def __init__(self, idx, node, ctype, position, moment_drive, output = 'yes'):
        assert isinstance(position, Position), (
            '\n-------------------\nERROR:' + 
            ' in defining a structural couple, the relative arm must be' +
            ' an instance of the Position class;' + 
            '\n-------------------\n')
        assert ctype in {'absolute', 'follower'}, (
            '\n-------------------\nERROR:' + 
            ' unrecognised type of structural couple: ' + str(ctype) + 
            ';\n-------------------\n')
        self.idx = idx
        self.type = 'couple'
        self.node = node
        self.ctype = ctype
        self.position = position
        self.moment_drive = moment_drive
        self.output = output
    def __str__(self):
        s = 'couple: ' + str(self.idx) + ', ' + self.ctype
        s = s + ',\n\t' + str(self.node)
        if len(self.position):
            s = s + ',\n\t\tposition, ' + str(self.position)
        s = s + ',\n\t\t' + ', '.join(str(i) for i in self.moment_drive)
        if self.output != 'yes':
            s = s + ',\n\toutput, ' + str(self.output)
        s = s + ';\n'
        return s


class StructuralInternalCouple(Element):
    def __init__(self, idx, nodes, ctype, positions, moment_drive, output = 'yes'):
        assert len(nodes) == 2, (
            '\n-------------------\nERROR:' + 
            ' defining a structural internal couple with ' + str(len(nodes)) +
            ' nodes' + '\n-------------------\n')
        assert len(positions) == 2, (
            '\n-------------------\nERROR:' + 
            ' defining a structural internal couple with ' + str(len(positions)) + 
            ' relative positions (!= 2);' +
            '\n-------------------\n')
        assert all(isinstance(pos, Position) for pos in positions), (
            '\n-------------------\nERROR:' + 
            ' in defining a structural internal couple all the relative positions ' +
            ' must be instances of the Position class;' + 
            '\n-------------------\n')
        assert ctype in {'absolute', 'follower'}, (
            '\n-------------------\nERROR:' + 
            ' unrecognised type of structural internal couple: ' + str(ctype) + 
            '\n-------------------\n')
        self.idx = idx
        self.type = 'couple'
        self.nodes = nodes
        self.ctype = ctype
        self.positions = positions
        self.moment_drive = moment_drive
        self.output = output
    def __str__(self):
        s = 'couple: ' + str(self.idx) + ', ' + self.ctype + ' inernal'
        s = s + ',\n\t' + str(self.nodes[0])
        s = s + ',\n\t\tposition, ' + str(self.position[0])
        s = s + ',\n\t' + str(self.nodes[1])
        s = s + ',\n\t\tposition, ' + str(self.position[1])
        s = s + ',\n\t\t' + ', '.join(str(i) for i in self.moment_drive)
        if self.output != 'yes':
            s = s + ',\n\toutput, ' + str(self.output)
        s = s + ';\n'
        return s


class Clamp(Element):
    def __init__(self, idx, node, pos = Position('', 'node'), 
            orient = Position('', 'node'), output = 'yes'):
        self.idx = idx
        self.type = 'joint'
        self.node = node
        self.position = pos
        self.orientation = orient
        self.output = output
    def __str__(self):
        s = 'joint: ' + str(self.idx) + ', clamp, ' + str(self.node) + ',\n'
        s = s + '\tposition, ' + str(self.position) + ',\n'
        s = s + '\torientation, ' + str(self.orientation)
        if self.output != 'yes':
            s = s + ',\n\toutput, ' + str(self.output)
        s = s + ';\n'
        return s


class TotalJoint(Element):
    def __init__(self, idx, nodes, positions, \
            position_orientations, rotation_orientations, \
            position_constraints, orientation_constraints, \
            position_drive, orientation_drive,
            output = 'yes'):
        assert isinstance(nodes, list), (
            '\n-------------------\nERROR:' + 
            ' in defining a total joint, the' +
            ' nodes must be given in a list' + 
            '\n-------------------\n')
        assert len(nodes) == 2, (
            '\n-------------------\nERROR:' + 
            ' defining a total joint with ' + str(len(nodes)) +
            ' nodes' + '\n-------------------\n')
        assert isinstance(positions, list), (
            '\n-------------------\nERROR:' + 
            ' in defining a total joint, the' +
            ' relative positions must be given in a list' + 
            '\n-------------------\n')    
        assert len(nodes) == len(positions), (
            '\n-------------------\nERROR:' +
            ' defining a total joint with ' + str(len(nodes)) +
            ' nodes and ' + str(len(positions)) + ' relative positions;\n' +
            '\n-------------------\n')
        assert isinstance(position_orientations, list), (
            '\n-------------------\nERROR:' + 
            ' in defining a total joint, the' +
            ' relative position orientations must be given in a list' + 
            '\n-------------------\n')
        assert len(nodes) == len(position_orientations), (
            '\n-------------------\nERROR:' +
            ' defining a total joint with ' + str(len(nodes)) +
            ' nodes and ' + str(len(position_orientations)) + ' position orientations;\n' +
            '\n-------------------\n')
        assert isinstance(rotation_orientations, list), (
            '\n-------------------\nERROR:' + 
            ' in defining a total joint, the' +
            ' relative rotation orientations must be given in a list' + 
            '\n-------------------\n')
        assert len(nodes) == len(rotation_orientations), (
            '\n-------------------\nERROR:' +
            ' defining a total joint with ' + str(len(nodes)) +
            ' nodes and ' + str(len(rotation_orientations)) + ' rotation orientations;\n' +
            '\n-------------------\n')
        assert isinstance(position_constraints, list), (
            '\n-------------------\nERROR:' +
            ' in defining a total joint, ' 
            ' position constraints must be given as a list;' + 
            '\n-------------------\n')
        assert len(position_constraints) == 3, (
            '\n-------------------\nERROR:' +
            ' defining a total joint with ' +
            str(len(position_constraints)) + ' position constraints;\n' +
            '\n-------------------\n')
        assert isinstance(orientation_constraints, list), (
            '\n-------------------\nERROR:' +
            ' in defining a total joint, ' 
            ' orientation constraints must be given as a list;' + 
            '\n-------------------\n')    
        assert len(orientation_constraints) == 3, (
            '\n-------------------\nERROR:' +
            ' defining a total joint with ' +
            str(len(orientation_constraints)) + ' orientation constraints;\n' +
            '\n-------------------\n')
        assert all([isinstance(pos, Position) for pos in positions]), (
            '\n-------------------\nERROR:' +
            ' in defining a total joint all offsets must be instances of ' + 
            ' the class Position;\n' +
            '\n-------------------\n')
        self.idx = idx
        self.type = 'joint'
        self.nodes = nodes
        self.positions = positions
        self.position_orientations = position_orientations
        self.rotation_orientations = rotation_orientations
        self.position_constraints = position_constraints
        self.orientation_constraints = orientation_constraints
        self.position_drive = position_drive
        self.orientation_drive = orientation_drive
        self.output = output
    def __str__(self):
        s = 'joint: ' + str(self.idx) + ', total joint'
        for (node, pos, pos_or, rot_or) in zip(self.nodes, self.positions,
                self.position_orientations, self.rotation_orientations):
            s = s + ',\n\t' + str(node)
            if not(pos.isnull()):
                s = s + ',\n\t\tposition, ' + str(pos)
            if not(pos_or.iseye()):
                s = s + ',\n\t\tposition orientation, ' + str(pos_or)
            if not(rot_or.iseye()):
                s = s + ',\n\t\trotation orientation, ' + str(rot_or)
        if sum(self.position_constraints):
            s = s + ',\n\tposition constraint, '\
                    + ', '.join(str(pc) for pc in self.position_constraints)
            if isinstance(self.position_drive, list):
                s = s + ',\n\t\t' + ', '.join(str(i) for i in self.position_drive)
            else:
                s = s + ',\n\t\t' + str(self.position_drive)
        if sum(self.orientation_constraints):
            s = s + ',\n\torientation constraint, '\
                    + ', '.join(str(oc) for oc in self.orientation_constraints)
            if isinstance(self.orientation_drive, list):
                s = s + ',\n\t\t' + ', '.join(str(i) for i in self.orientation_drive)
            else:
                s = s + ',\n\t\t', + str(self.orientation_drive)
        if self.output != 'yes':
            s = s + ',\n\toutput, ' + str(self.output)
        s = s + ';\n'
        return s


class TotalPinJoint(Element):
    def __init__(self, idx, node, 
            positions, position_orientations, rotation_orientations, 
            position_constraints, orientation_constraints, 
            position_drive, orientation_drive,
            output = 'yes'):
        if not isinstance(positions, list):
            positions = [positions]
        assert (len(positions) in [1, 2]) and all([isinstance(pos, Position) for pos in positions]), (
            '\n-------------------\nERROR:' +
            ' in defining a total pin joint, ' + 
            ' relative positions must be given as a single instance' + 
            ' of the Position class or as a list of Position instances' + 
            '\n-------------------\n')
        if not isinstance(position_orientations, list):
            position_orientations = [position_orientations]
        assert ((len(position_orientations) in [1, 2]) and all([isinstance(pos, Position) for pos in position_orientations])), (
            '\n-------------------\nERROR:' +
            ' in defining a total pin joint, ' + 
            ' relative position orientations must be given as a single instance' + 
            ' of the Position class or as a list of Position instances' + 
            '\n-------------------\n')
        if not isinstance(rotation_orientations, list):
            rotation_orientations = [rotation_orientations]
        assert ((len(rotation_orientations) in [1, 2]) and all([isinstance(pos, Position) for pos in rotation_orientations])), (
            '\n-------------------\nERROR:' +
            ' in defining a total pin joint, ' + 
            ' relative rotation orientations must be given as a single instance' + 
            ' of the Position class or as a list of Position instances' + 
            '\n-------------------\n')
        assert isinstance(position_constraints, list), (
            '\n-------------------\nERROR:' +
            ' in defining a total joint, ' 
            ' position constraints must be given as a list;' + 
            '\n-------------------\n')
        assert len(position_constraints) == 3, (
            '\n-------------------\nERROR:' +
            ' defining a total joint with ' + str(len(position_constraints)) + 
            ' position constraints;' + '\n-------------------\n')
        assert isinstance(orientation_constraints, list), (
            '\n-------------------\nERROR:' +
            ' in defining a total joint, ' 
            ' orientation constraints must be given as a list;' + 
            '\n-------------------\n')
        assert len(orientation_constraints) == 3, (
            '\n-------------------\nERROR:' +
            ' defining a total joint with ' + str(len(orientation_constraints)) + 
            ' orientation constraints;' + '\n-------------------\n')
        self.idx = idx
        self.type = 'joint'
        self.node = node
        self.positions = positions
        self.position_orientations = position_orientations
        self.rotation_orientations = rotation_orientations
        self.position_constraints = position_constraints
        self.orientation_constraints = orientation_constraints
        self.position_drive = position_drive
        self.orientation_drive = orientation_drive
        self.output = output
    def __str__(self):
        s = 'joint: ' + str(self.idx) + ', total pin joint'
        s = s + ',\n\t' + str(self.node)
        if not(self.positions[0].isnull()):
            s = s + ',\n\t\tposition, ' + str(self.positions[0])
        if not(self.position_orientations[0].iseye()):
            s = s + ',\n\t\tposition orientation, ' + str(self.position_orientations[0])
        if not(self.rotation_orientations[0].iseye()):
            s = s + ',\n\t\trotation orientation, ' + str(self.rotation_orientations[0])
        if len(self.positions) == 2 and not(self.positions[1].isnull()):
            s = s + ',\n\t# GROUND'
            s = s + '\n\t\tposition, ' + str(self.positions[1])
        if len(self.position_orientations) == 2 and not(self.position_orientations[1].iseye()):
            s = s + ',\n\t\tposition orientation, ' + str(self.position_orientations[1])
        if len(self.rotation_orientations) == 2 and not(self.rotation_orientations[1].iseye()):
            s = s + ',\n\t\trotation orientation, ' + str(self.rotation_orientations[1])
        if sum(self.position_constraints):
            s = s + ',\n\tposition constraint, '\
                    + ', '.join(str(pc) for pc in self.position_constraints)
            s = s + ',\n\t\t' + ', '.join(str(i) for i in self.position_drive)
        if sum(self.orientation_constraints):
            s = s + ',\n\torientation constraint, '\
                    + ', '.join(str(oc) for oc in self.orientation_constraints)
            s = s + ',\n\t\t' + ', '.join(str(i) for i in self.orientation_drive)
        if self.output != 'yes':
            s = s + ',\n\toutput, ' + str(self.output)
        s = s + ';\n'
        return s

class JointRegularization(Element):
    def __init__(self, idx, coefficients):
        assert (isinstance(coefficients, list) and len(coefficients) >= 1) or (isinstance(coefficients, Number)), (
            '\n-------------------\nERROR:' + 
            ' joint regularization needs at least one' +
            ' coefficient ' + '\n-------------------\n')
        self.idx = idx
        self.type = 'joint regularization'
        self.coefficients = coefficients
    def __str__(self):
        s = 'joint regularization: ' + str(self.idx) + ", tikhonov"
        if isinstance(self.coefficients, list):
            s = s + 'list, ' + ', '.join(str(co) for co in self.coefficients)
        else:
            s = s + ', ' + str(self.coefficients)
        s = s + ';\n'
        return s


class Rod(Element):
    def __init__(self, idx, nodes, positions, const_law, length = 'from nodes', 
            output = 'yes'):
        assert len(nodes) == 2, (
            '\n-------------------\nERROR:' + 
            ' defining a rod with ' + str(len(nodes)) +
            ' nodes' + '\n-------------------\n')
        assert len(nodes) == len(positions), (
            '\n-------------------\nERROR:' +
            ' defining a rod with ' + str(len(nodes)) +
            ' nodes and ' + str(len(positions)) + ' relative positions;\n' +
            '\n-------------------\n')
        if not isinstance(positions, list):
            positions = [positions]
        assert all([isinstance(pos, Position) for pos in positions]), (
            '\n-------------------\nERROR:' +
            ' in defining a rod all offsets must be instances of ' + 
            ' the class Position;\n' +
            '\n-------------------\n')
        self.idx = idx
        self.type = 'joint'
        self.nodes = nodes
        self.positions = positions
        self.const_law = const_law
        self.length = length
        self.output = output
    def __str__(self):
        s = 'joint: ' + str(self.idx) + ', rod'
        for (node, position) in zip(self.nodes, self.positions):
            s = s + ',\n\t' + str(node)
            if not(position.isnull()):
                s = s + ',\n\t\tposition, ' + str(position)
        s = s + ',\n\t' + str(self.length) + ',\n'
        s = s + '\t' + ', '.join(str(i) for i in self.const_law)
        if self.output != 'yes':
            s = s + ',\n\toutput, ' + str(self.output)
        s = s + ';\n'
        return s
    
class CardanoHinge(Element):
    def __init__(self, idx, nodes, positions, orientations, output = 'yes'):
        assert isinstance(nodes, list), (
            '\n-------------------\nERROR:' +
            ' in defining a cardano hinge, the' +
            ' nodes must be given in a list' +
            '\n-------------------\n')
        assert len(nodes) == 2, (
            '\n-------------------\nERROR:' +
            ' defining a cardano hinge with ' + str(len(nodes)) +
            ' nodes' + '\n-------------------\n')
        assert isinstance(positions, list), (
            '\n-------------------\nERROR:' +
            ' in defining a cardano hinge, the' +
            ' relative positions must be given in a list' +
            '\n-------------------\n')
        assert len(nodes) == len(positions), (
            '\n-------------------\nERROR:' +
            ' defining a cardano hinge with ' + str(len(nodes)) +
            ' nodes and ' + str(len(positions)) + ' relative positions;\n' +
            '\n-------------------\n')
        assert isinstance(orientations, list), (
            '\n-------------------\nERROR:' +
            ' in defining a cardano hinge, the' +
            ' relative position orientations must be given in a list' +
            '\n-------------------\n')
        self.idx = idx
        self.type = 'joint'
        self.nodes = nodes
        self.positions = positions
        self.orientations = orientations
        self.output = output
    def __str__(self):
        s = 'joint: ' + str(self.idx) + ', cardano hinge'
        for (node, pos, orient) in zip(self.nodes, self.positions, self.orientations):
            s = s + ',\n\t' + str(node)
            if not(pos.isnull()):
                s = s + ',\n\t\tposition, ' + str(pos)
            if not(orient.iseye()):
                s = s + ',\n\t\torientation, ' + str(orient)
        if self.output != 'yes':
            s = s + ',\n\toutput, ' + str(self.output)
        s = s + ';\n'
        return s

class DeformableDiaplacement(Element):
    def __init__(self, idx, nodes, positions, orientations, const_law, output = 'yes'):
        assert isinstance(nodes, list), (
            '\n-------------------\nERROR:' +
            ' in defining a deformable displacement joint, the' +
            ' nodes must be given in a list' +
            '\n-------------------\n')
        assert len(nodes) == 2, (
            '\n-------------------\nERROR:' +
            ' defining a deformable displacement joint with ' + str(len(nodes)) +
            ' nodes' + '\n-------------------\n')
        assert isinstance(positions, list), (
            '\n-------------------\nERROR:' +
            ' in defining a deformable displacement joint, the' +
            ' relative positions must be given in a list' +
            '\n-------------------\n')
        assert len(nodes) == len(positions), (
            '\n-------------------\nERROR:' +
            ' defining a deformable displacement joint with ' + str(len(nodes)) +
            ' nodes and ' + str(len(positions)) + ' relative positions;\n' +
            '\n-------------------\n')
        assert isinstance(orientations, list), (
            '\n-------------------\nERROR:' +
            ' in defining a deformable displacement joint, the' +
            ' relative position orientations must be given in a list' +
            '\n-------------------\n')
        self.idx = idx
        self.type = 'joint'
        self.nodes = nodes
        self.positions = positions
        self.orientations = orientations
        self.constitutive_law = const_law
    def __str__(self):
        s = 'joint: ' + str(self.idx) + ', deformable displacement'
        for (node, pos, orient) in zip(self.nodes, self.positions, self.orientations):
            s = s + ',\n\t' + str(node)
            if not(pos.isnull()):
                s = s + ',\n\t\tposition, ' + str(pos)
            if not(self.pos_or.iseye()):
                s = s + ',\n\t\torientation, ' + str(orient)
        s = s + '\n\t'
        if isinstance(self.constitutive_law, str):
            s = s + self.constitutive_law
        else:
            s = s + ', '.join(str(i) for i in self.constitutive_law)
        if self.output != 'yes':
            s = s + ',\n\toutput, ' + str(self.output)
        s = s + ';\n'
        return s

class DeformableHinge(Element):
    def __init__(self, idx, nodes, positions, orientations, const_law, output = 'yes'):
        assert isinstance(nodes, list), (
            '\n-------------------\nERROR:' +
            ' in defining a deformable hinge, the' +
            ' nodes must be given in a list' +
            '\n-------------------\n')
        assert len(nodes) == 2, (
            '\n-------------------\nERROR:' +
            ' defining a deformable hinge with ' + str(len(nodes)) +
            ' nodes' + '\n-------------------\n')
        assert isinstance(positions, list), (
            '\n-------------------\nERROR:' +
            ' in defining a deformable hinge, the' +
            ' relative positions must be given in a list' +
            '\n-------------------\n')
        assert len(nodes) == len(positions), (
            '\n-------------------\nERROR:' +
            ' defining a deformable hinge with ' + str(len(nodes)) +
            ' nodes and ' + str(len(positions)) + ' relative positions;\n' +
            '\n-------------------\n')
        assert isinstance(orientations, list), (
            '\n-------------------\nERROR:' +
            ' in defining a deformable hinge, the' +
            ' relative position orientations must be given in a list' +
            '\n-------------------\n')
        self.idx = idx
        self.type = 'joint'
        self.nodes = nodes
        self.positions = positions
        self.orientations = orientations
        self.constitutive_law = const_law
        self.output = output
    def __str__(self):
        s = 'joint: ' + str(self.idx) + ', deformable hinge'
        for (node, pos, orient) in zip(self.nodes, self.positions, self.orientations):
            s = s + ',\n\t' + str(node)
            if not(pos.isnull()):
                s = s + ',\n\t\tposition, ' + str(pos)
            if not(orient.iseye()):
                s = s + ',\n\t\torientation, ' + str(orient)
        s = s + ',\n\t'
        if isinstance(self.constitutive_law, str):
            s = s + self.constitutive_law
        else:
            s = s + ', '.join(str(i) for i in self.constitutive_law)
        if self.output != 'yes':
            s = s + ',\n\toutput, ' + str(self.output)
        s = s + ';\n'
        return s
    
class DeformableJoint(Element):
    def __init__(self, idx, nodes, positions, orientations, const_law, output = 'yes'):
        assert isinstance(nodes, list), (
            '\n-------------------\nERROR:' +
            ' in defining a deformable joint, the' +
            ' nodes must be given in a list' +
            '\n-------------------\n')
        assert len(nodes) == 2, (
            '\n-------------------\nERROR:' +
            ' defining a deformable joint with ' + str(len(nodes)) +
            ' nodes' + '\n-------------------\n')
        assert isinstance(positions, list), (
            '\n-------------------\nERROR:' +
            ' in defining a deformable joint, the' +
            ' relative positions must be given in a list' +
            '\n-------------------\n')
        assert len(nodes) == len(positions), (
            '\n-------------------\nERROR:' +
            ' defining a deformable joint with ' + str(len(nodes)) +
            ' nodes and ' + str(len(positions)) + ' relative positions;\n' +
            '\n-------------------\n')
        assert isinstance(orientations, list), (
            '\n-------------------\nERROR:' +
            ' in defining a deformable joint, the' +
            ' relative position orientations must be given in a list' +
            '\n-------------------\n')
        self.idx = idx
        self.type = 'joint'
        self.nodes = nodes
        self.positions = positions
        self.orientations = orientations
        self.constitutive_law = const_law
    def __str__(self):
        s = 'joint: ' + str(self.idx) + ', deformable joint'
        for (node, pos, orient) in zip(self.nodes, self.positions, self.orientations):
            s = s + ',\n\t' + str(node)
            if not(pos.isnull()):
                s = s + ',\n\t\tposition, ' + str(pos)
            if not(self.pos_or.iseye()):
                s = s + ',\n\t\torientation, ' + str(orient)
        s = s + '\n\t'
        if isinstance(self.constitutive_law, str):
            s = s + self.constitutive_law
        else:
            s = s + ', '.join(str(i) for i in self.constitutive_law)
        if self.output != 'yes':
            s = s + ',\n\toutput, ' + str(self.output)
        s = s + ';\n'
        return s
    
class SphericalHinge(Element):
    def __init__(self, idx, nodes, positions, orientations, output = 'yes'):
        assert isinstance(nodes, list), (
            '\n-------------------\nERROR:' +
            ' in defining a spherical hinge, the' +
            ' nodes must be given in a list' +
            '\n-------------------\n')
        assert len(nodes) == 2, (
            '\n-------------------\nERROR:' +
            ' defining a spherical hinge with ' + str(len(nodes)) +
            ' nodes' + '\n-------------------\n')
        assert isinstance(positions, list), (
            '\n-------------------\nERROR:' +
            ' in defining a spherical hinge, the' +
            ' relative positions must be given in a list' +
            '\n-------------------\n')
        assert len(nodes) == len(positions), (
            '\n-------------------\nERROR:' +
            ' defining a spherical hinge with ' + str(len(nodes)) +
            ' nodes and ' + str(len(positions)) + ' relative positions;\n' +
            '\n-------------------\n')
        assert isinstance(orientations, list), (
            '\n-------------------\nERROR:' +
            ' in defining a spherical hinge, the' +
            ' relative position orientations must be given in a list' +
            '\n-------------------\n')
        self.idx = idx
        self.type = 'joint'
        self.nodes = nodes
        self.positions = positions
        self.orientations = orientations
        self.output = output
    def __str__(self):
        s = 'joint: ' + str(self.idx) + ', spherical hinge'
        for (node, pos, orient) in zip(self.nodes, self.positions, self.orientations):
            s = s + ',\n\t' + str(node)
            if not(pos.isnull()):
                s = s + ',\n\t\tposition, ' + str(pos)
            if not(orient.iseye()):
                s = s + ',\n\t\torientation, ' + str(orient)
        if self.output != 'yes':
            s = s + ',\n\toutput, ' + str(self.output)
        s = s + ';\n'
        return s

class Shell(Element):
    def __init__(self, shell_type, idx, nodes, const_law, output = 'yes'):
        self.idx = idx
        self.type = shell_type
        self.nodes = nodes
        if isinstance(const_law, list):
            self.const_law = const_law
        else:
            self.const_law = [const_law]
        self.output = output
    def __str__(self):
        s = str(self.type) + ': ' + str(self.idx) + ',\n'
        s = s + '\t' + ', '.join(str(i) for i in self.nodes) + ',\n'
        s = s + '\t' + ', '.join(str(i) for i in self.const_law)
        if self.output != 'yes':
            s = s + ',\n\toutput, ' + str(self.output)
        s = s + ';\n'
        return s
        
class Beam(Element):
    def __init__(self, idx, nodes, positions, orientations, const_laws_orientations,
            const_laws, output = 'yes'):
        assert len(nodes) == 3 or len(nodes) == 2, (
            '\n-------------------\nERROR:' + 
            ' defining a beam with ' + str(len(nodes)) +
            ' nodes' + '\n-------------------\n')
        assert len(nodes) == len(positions), (
            '\n-------------------\nERROR:' +
            ' defining a beam with ' + str(len(nodes)) +
            ' nodes and ' + str(len(positions)) + ' relative positions;\n' +
            '\n-------------------\n')
        assert len(nodes) == len(orientations), (
            '\n-------------------\nERROR:' +
            ' defining a beam with ' + str(len(nodes)) +
            ' nodes and ' + str(len(orientations)) + ' relative orientations;\n' +
            '\n-------------------\n')
        assert len(const_laws_orientations) == len(const_laws), (
            '\n-------------------\nERROR:' +
            ' defining a beam with ' + str(len(const_laws)) +
            ' coonstitutive laws and ' + str(len(const_laws_orientations)) + ' constitutive law orientations;' +
            '\n-------------------\n')
        if len(nodes) == 2:
            self.type = 'beam2'
        else:
            self.type = 'beam3'
        self.idx = idx
        self.nodes = nodes
        self.positions = positions
        self.orientations = orientations
        self.const_laws_orientations = const_laws_orientations
        self.const_laws = const_laws
        self.output = output

    def format_const_law(self, cl):
        """Helper method to format constitutive law lists"""
        if isinstance(cl, list):
            return ', '.join(str(x) for x in cl)
        return str(cl)

    def __str__(self):
        s = str(self.type) + ': ' + str(self.idx)
        for (node, position, orientation) in zip(self.nodes, self.positions, self.orientations):
            s = s + ',\n\t' + str(node) + ',\n\t\tposition, ' + str(position) + ',\n\t\torientation, ' + str(orientation)
        for (cl_or, cl) in zip(self.const_laws_orientations, self.const_laws):
            s = s + ',\n\t' + str(cl_or) + ',\n\t'
            s += self.format_const_law(cl)
        if self.output != 'yes':
            s = s + ',\n\toutput, ' + str(self.output)
        s = s + ';\n'
        return s
    
if imported_pydantic:
    BeamSlider.model_rebuild()

class AerodynamicBody(Element):
    def __init__(self, idx, node, 
            position, orientation, span,
            chord, aero_center, b_c_point, twist, integration_points,
            induced_velocity = [], tip_loss = [], control = [], 
            airfoil_data = [], unsteady = [], 
            jacobian = 'no', custom_output = [], output = 'yes'):
        assert isinstance(position, Position), (
            '\n-------------------\nERROR:' + 
            ' in defining an aerodynamic body the' + 
            ' relative surface offset must be an instance of the' + 
            ' Position class;' + '\n-------------------\n')
        assert isinstance(orientation, Position), (
            '\n-------------------\nERROR:' + 
            ' in defining an aerodynamic body the '
            ' relative surface orientation must be an instance of the' 
            ' Position class;' + '\n-------------------\n')
        assert isinstance(span, (Number)) or (isinstance(span, MBVar) and (span.var_type in ('real', 'const real'))), (
            '\n-------------------\nERROR:' + 
            ' in defining an aerodynamic body, the' + 
            ' surface span must be numeric' + 
            '\n-------------------\n')
        assert (isinstance(integration_points, Integral) and (integration_points > 0)) \
                or (isinstance(integration_points, MBVar) and integration_points.var_type in ('integer', 'const integer')), (
            '\n-------------------\nERROR:' + 
            ' defining an aerodynamic body with ' + str(integration_points) +
            ' integration_points' + '\n-------------------\n')
        assert (induced_velocity == []) or isinstance(induced_velocity, (Integral, MBVar)), (
            '\n-------------------\nERROR:' + 
            ' in defining an aerodynamic body the '
            ' induced velocity elment tag must be an integer or MBVar;' 
            '\n-------------------\n')
        assert not(len(unsteady)) or ((len(unsteady) > 0)*'bielawa' == 'bielawa'), (
            '\n-------------------\nERROR:' + 
            ' defining an aerodynamic body with unrecognised unsteady flag'
            '\n-------------------\n')
        assert (jacobian in {'yes', 'no'}) or isinstance(jacobian, bool), (
            '\n-------------------\nERROR:' + 
            ' defining an aerodynamic body with unrecognised jacobian flag'
            '\n-------------------\n')
        self.idx = idx
        self.type = 'aerodynamic body'
        self.node = node
        self.position = position
        self.orientation = orientation
        self.span = span
        self.chord = chord
        self.aero_center = aero_center
        self.b_c_point = b_c_point
        self.twist = twist
        self.integration_points = integration_points
        self.induced_velocity = induced_velocity
        self.tip_loss = tip_loss
        self.control = control
        self.airfoil_data = airfoil_data
        self.unsteady = unsteady
        self.jacobian = jacobian
        self.custom_output = custom_output
        self.output = output
    def __str__(self):
        s = 'aerodynamic body: ' + str(self.idx)
        s = s + ',\n\t ' + str(self.node)
        if self.induced_velocity:
            s = s + ',\n\t\tinduced velocity ' + str(self.induced_velocity)
        s = s + ',\n\t\t' + str(self.position)
        s = s + ',\n\t\t' + str(self.orientation)
        s = s + ',\n\t\t' + str(self.span)
        s = s + ',\n\t\t' + ', '.join(str(i) for i in self.chord)
        s = s + ',\n\t\t' + ', '.join(str(i) for i in self.aero_center)
        s = s + ',\n\t\t' + ', '.join(str(i) for i in self.b_c_point)
        s = s + ',\n\t\t' + ', '.join(str(i) for i in self.twist)
        if len(self.tip_loss):
            s = s + ',\n\t\ttip loss, ' + ', '.join(str(i) for i in self.tip_loss)
        s = s + '\n\t\t' + str(self.integration_points)
        if len(self.control):
            s = s + ',\n\t\tcontrol, ' + ', '.join(str(i) for i in self.control)
        if len(self.airfoil_data):
            s = s + ',\n\t\t' + ', '.join(str(i) for i in self.airfoil_data)
        if len(self.unsteady):
            s = s + ',\n\t\tunsteady, ' + str(self.unsteady)
        if len(self.jacobian):
            s = s + ',\n\t\tjacobian, ' + str(self.jacobian)
        if self.output != 'yes':
            s = s + ',\n\toutput, ' + str(self.output)
        if len(self.custom_output):
            s = s + ',\n\tcustom output, ' + ', '.join(str(i) for i in self.custom_output)
        s = s + ';\n'
        return s


class AerodynamicBeam(Element):
    def __init__(self, idx, beam, 
            positions, orientations,
            chord, aero_center, b_c_point, twist, integration_points, 
            induced_velocity = [], tip_loss = [], control = [], 
            airfoil_data = [], unsteady = [], 
            jacobian = 'no', custom_output = [], output = 'yes'):
        assert len(positions) in {2,3}, (
            '\n-------------------\nERROR:' + 
            ' defining an aerodynamic beam with ' + str(len(positions)) +
            ' relative surface offsets (not in [2,3])' + '\n-------------------\n')
        assert all(isinstance(pos, Position) for pos in positions), (
            ' in defining an aerodynamic beam the' + 
            ' relative surface offsets must be instances of the' + 
            ' Position class;' + '\n-------------------\n')
        assert len(orientations) in {2,3}, (
            '\n-------------------\nERROR:' + 
            ' defining an aerodynamic beam with ' + str(len(orientations)) +
            ' relative surface orientations (not in [2,3])' + '\n-------------------\n')
        assert all(isinstance(pos, Position) for pos in orientations), (
            ' in defining an aerodynamic beam the' + 
            ' relative surface orientations must be instances of the' + 
            ' Position class;' + '\n-------------------\n')
        assert len(positions) == len(orientations), (
            '\n-------------------\nERROR:' + 
            ' definining an aerodynamic beam with ' + str(len(positions)) + 
            ' relative surface offsets and ' + str(len(orientations)) + 
            ' relative surface orientations' + '\n-------------------\n')
        assert (isinstance(integration_points, Integral) and (integration_points > 0))\
                or (isinstance(integration_points, MBVar) and integration_points.var_type in ('integer', 'const integer')), (
            '\n-------------------\nERROR:' + 
            ' defining an aerodynamic beam with ' + str(integration_points) +
            ' integration_points' + '\n-------------------\n')
        assert (induced_velocity == []) or isinstance(induced_velocity, (Integral, MBVar)), (
            '\n-------------------\nERROR:' + 
            ' in defining an aerodynamic body the '
            ' induced velocity elment tag must be an integer or an MBVar;' 
            '\n-------------------\n')
        assert not(len(unsteady)) or ((len(unsteady) > 0)*'bielawa' == 'bielawa'), (
            '\n-------------------\nERROR:' + 
            ' defining an aerodynamic beam with unrecognised unsteady flag'
            '\n-------------------\n')
        assert (jacobian in {'yes', 'no'}) or isinstance(jacobian, bool), (
            '\n-------------------\nERROR:' + 
            ' defining an aerodynamic beam with unrecognised jacobian flag'
            '\n-------------------\n')
        self.idx = idx
        self.type = 'aerodynamic beam' + str(len(self.positions))
        self.beam = beam
        self.positions = positions
        self.orientations = orientations
        self.chord = chord
        self.aero_center = aero_center
        self.b_c_point = b_c_point
        self.twist = twist
        self.integration_points = integration_points
        self.induced_velocity = induced_velocity
        self.tip_loss = tip_loss
        self.control = control
        self.airfoil_data = airfoil_data
        self.unsteady = unsteady
        self.jacobian = jacobian
        self.custom_output = custom_output
        self.output = output
    def __str__(self):
        s = 'aerodynamic beam' + str(len(self.positions)) + ': ' + str(self.idx)
        s = s + ',\n\t ' + str(self.beam)
        if self.induced_velocity:
            s = s + ',\n\t\tinduced velocity ' + str(self.induced_velocity)
        for (pos, ori) in zip(self.positions, self.orientations):
            s = s + ',\n\t\t' + str(pos)
            s = s + ',\n\t\t' + str(ori)
        s = s + ',\n\t\t' + ', '.join(str(i) for i in self.chord)
        s = s + ',\n\t\t' + ', '.join(str(i) for i in self.aero_center)
        s = s + ',\n\t\t' + ', '.join(str(i) for i in self.b_c_point)
        s = s + ',\n\t\t' + ', '.join(str(i) for i in self.twist)
        if len(self.tip_loss):
            s = s + ',\n\t\ttip loss, ' + ', '.join(str(i) for i in self.tip_loss)
        s = s + ',\n\t\t' + str(self.integration_points)
        if len(self.control):
            s = s + ',\n\t\tcontrol, ' + ', '.join(str(i) for i in self.control)
        if len(self.airfoil_data):
            s = s + ',\n\t\t' + ', '.join(str(i) for i in self.airfoil_data)
        if len(self.unsteady):
            s = s + ',\n\t\tunsteady, ' + str(self.unsteady)
        if self.jacobian == 'yes':
            s = s + ',\n\t\tjacobian, ' + str(self.jacobian)
        if self.output != 'yes':
            s = s + ',\n\toutput, ' + str(self.output)
        if len(self.custom_output):
            s = s + ',\n\tcustom output, ' + ', '.join(str(i) for i in self.custom_output)
        s = s + ';\n'
        return s

# General stuff
class NodeDof:
    idx = -1
    def __init__(self, **kwargs):
        try:
            assert isinstance(kwargs['node_label'], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' NodeDof: <node_label> must either be an integer value or an MBVar' + 
                    '\n-------------------\n')
            self.node_label = kwargs['node_label']
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' NodeDof: <node_label> must be provided' + 
                    '\n-------------------\n'
            )
        try:
            if kwargs['node_type'] not in ('abstract', 'electric', 'hydraulic', 'parameter', 'structural', 'thermal'):
                raise ValueError(
                    '\n-------------------\nERROR:' +
                    ' NodeDof: <node_type> must be either \'abstract\', \'electric\'' +
                    ' \'hydraulic\', \'parameter\', \'structural\', \'thermal\'' +
                    '\n-------------------\n'
                    )
            else:
                self.node_type = kwargs['node_type']
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' NodeDof: <node_type> must be provided' +
                    '\n-------------------\n'
                    )
        try:
            assert isinstance(kwargs['dof_number'], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' NodeDof: <dof_number> must either be an integer value or an MBVar' + 
                    '\n-------------------\n')
            self.dof_number = kwargs['dof_number']
        except KeyError:
            pass
        try:
            if kwargs['dof_order'] not in ('algebraic', 'differential'):
                raise ValueError(
                    '\n-------------------\nERROR:' +
                    ' NodeDof: <dof_order> must either be an integer value or an MBVar' + 
                    '\n-------------------\n'
                    )
            else:
                self.dof_order = kwargs['dof_order']
        except KeyError:
            pass
    def __str__(self):
        s = '{}, {}'.format(self.node_label, self.node_type)
        if hasattr(self, 'dof_number'):
            s = s + ', {}'.format(self.dof_number)
        if hasattr(self, 'dof_order'):
            s = s + ', {}'.format(self.dof_order)
        return s

# Drives
class DriveCaller():
    idx = -1

# TODO: Rename to DriveCaller when all are moved
class DriveCaller2(MBEntity):
    """
    Abstract class for C++ type `DriveCaller`. Every time some entity can be driven, i.e. a value can be expressed
    as dependent on some external input, an object of the class  `DriveCaller` is used.

    The `drive` essentially represents a scalar function, whose value can change over time or,
    through some more sophisticated means, can depend on the state of the analysis.
    Usually, the dependence over time is implicitly assumed, unless otherwise specified.

    For example, the amplitude of the force applied by a  `force` element is defined by means of a `drive`;
    as such, the value of the `drive` is implicitly calculated as a function of the time.
    However, a  `dof drive` uses a subordinate `drive` to compute its value based on the value of
    a degree of freedom of the analysis; as a consequence, the value of the `dof drive` is represented
    by the value of the subordinate `drive` when evaluated as a function of that specific degree of freedom
    at the desired time (function of function).

    The family of the `DriveCaller` object is very large.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    idx: Optional[Union[MBVar, int]] = None
    """Index of this drive to reuse with references"""

    @abstractmethod
    def drive_type(self) -> str:
        """Every drive class must define this to return its MBDyn syntax name"""
        raise NotImplementedError("called drive_type of abstract DriveCaller")

    def drive_header(self) -> str:
        """common syntax for start of any drive caller"""
        # it's not just `__str__` to still require overriding it in specific drives
        if self.idx is not None and self.idx >= 0:
            # The idx possibly being None communicates the intent more clearly than checking if it's >=0
            return f'drive caller: {self.idx}, {self.drive_type()}'
        else:
            return self.drive_type()

class ArrayDriveCaller(DriveCaller2):
    '''
    this is simply a front-end for the linear combination of <len(drives)> normal drives. <len(drives)> must be
    at least 1, in which case a simple drive caller is created, otherwise an array of drive callers is created and
    at every call their value is added to give the ﬁnal value of the array drive
    '''

    drives: List[Union[DriveCaller, DriveCaller2]]  #TODO: Remove DriveCaller2 when all are moved
    """List of drive callers to be used in the array"""

    @field_validator('drives')
    def validate_drives_not_empty(cls, v):
        """Validate that drives contains at least one drive caller"""
        if len(v) < 1:
            raise ValueError("array drive must contain at least one drive caller")
        return v

    def drive_type(self) -> str:
        return 'array'
    
    def __str__(self):
        return self._str_with_indent()
        
    def _str_with_indent(self, indent=""):
        """Helper method to handle indentation for nested arrays"""
        # Base string with appropriate indentation for current level
        s = self.drive_header()
        s += f", {len(self.drives)}"
        # Add each drive with appropriate indentation
        for drive in self.drives:
            if hasattr(drive, 'idx') and drive.idx is not None and drive.idx >= 0:
                s += f",\n{indent}\treference, {drive.idx}"
            elif isinstance(drive, ArrayDriveCaller):
                # For nested ArrayDriveCaller, increase indentation
                nested_str = drive._str_with_indent(indent + "\t")
                # Remove the header part before including
                if drive.idx is not None and drive.idx >= 0:
                    nested_str = nested_str.replace(f"drive caller: {drive.idx}, ", "")
                nested_str = nested_str.replace(f"{drive.drive_type()}", f"{indent}\t{drive.drive_type()}")
                s += f",\n{nested_str}"
            else:
                s += f",\n{indent}\t{drive}"
        return s

class BistopDriveCaller(DriveCaller2):
    '''
    This drive caller returns 1.0 (TRUE) when its status is active and 0.0 (FALSE) when it is inactive.
    When in inactive status, it turns to active if the activation_condition is TRUE. When in active
    status, it turns to inactive if the deactivation_condition is TRUE.
    This drive caller is useful to implement a “robust” and irreversible status change
    '''
    
    initial_status: Optional[Literal['active', 'inactive']] = 'active'
    activation_condition: DriveCaller2 
    deactivation_condition: DriveCaller2
    
    def drive_type(self) -> str:
        return 'bistop'
    
    def __str__(self):
        s = f'{self.drive_header()}'
        s += f',\n\tinitial status, {self.initial_status},'
        s += '\n\t# activation condition drive'
        if self.activation_condition.idx is not None and self.activation_condition.idx >= 0:
            s += f'\n\treference, {self.activation_condition.idx}'
        else:
            s += f'\n\t{self.activation_condition}'
        s += '\n\t# deactivation condition drive'
        if self.deactivation_condition.idx is not None and self.deactivation_condition.idx >= 0:
            s += f'\n\treference, {self.deactivation_condition.idx}'
        else:
            s += f'\n\t{self.deactivation_condition}'
        return s
    
# class BistopDriveCaller(DriveCaller):
#     type = 'bistop'
#     def __init__(self, **kwargs):
#         try:
#             if kwargs['initial_status'] in ['active', 'inactive']:
#                 self.initial_status = kwargs['initial status']
#             else:
#                 raise ValueError(
#                         '\n------------------\nERROR:' + 
#                         ' BistopDriveCaller: <initial_status> must be' + 
#                         ' either \'active\' or \'inactive\'' + 
#                         '\n------------------\n')
#         except KeyError:
#             self.initial_status = 'active'
#             pass
#         try:
#             assert isinstance(kwargs['idx'], (Integral, MBVar)), (
#                     '\n-------------------\nERROR:' +
#                     ' BistopDriveCaller: <idx> must either be an integer value or an MBVar' + 
#                     '\n-------------------\n')
#             self.idx = kwargs['idx']
#         except KeyError:
#             pass
#         assert isinstance(kwargs['activation_condition'], DriveCaller), (
#                 '\n-------------------\nERROR:' +
#                 ' BistopDriveCaller: <activation_condition> must be' + 
#                 ' a DriveCaller instance' + 
#                 '\n-------------------\n')

#         assert isinstance(kwargs['deactivation_condition'], DriveCaller), (
#                 '\n-------------------\nERROR:' +
#                 ' BistopDriveCaller: <deactivation_condition> must be' + 
#                 ' a DriveCaller instance' + 
#                 '\n-------------------\n')
#         self.activation_condition = kwargs['activation_condition']
#         self.deactivation_condition = kwargs['deactivation_condition']
#     def __str__(self):
#         s = ''
#         if self.idx >= 0:
#             s = s + 'drive caller: {}, '.format(self.idx)
#         s = s + '{},\n\tinitial status, {},'.format(self.type, self.initial_status)
#         s = s + '\n\t# activation condition drive'
#         if self.activation_condition.idx < 0:
#             s = s + '\n\t{}'.format(self.activation_condition)
#         else:
#             s = s + '\n\treference, {}'.format(self.activation_condition.idx)
#         s = s + '\n\t# deactivation condition drive'
#         if self.deactivation_condition.idx < 0:
#             s = s + '\n\t{}'.format(self.deactivation_condition)
#         else:
#             s = s + '\n\treference, {}'.format(self.deactivation_condition.idx)
#         return s


class ConstDriveCaller(DriveCaller2):
    """An example of `DriveCaller` that always returns the same constant value"""

    # Note that method docstrings are inherited correctly (unlike dataclass fields)
    def drive_type(self):
        return 'const'

    const_value: Union[MBVar, float, int]
    """Value that will be output by the drive"""

    def __str__(self):
        return f'''{self.drive_header()}, {self.const_value}'''
    
class ClosestNextDriveCaller(DriveCaller):
    type = 'closest next'
    def __init__(self, **kwargs):
        try:
            assert isinstance(kwargs['idx'], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' ClosestNextDriveCaller: <idx> must either be an integer value or an MBVar' + 
                    '\n-------------------\n')
            self.idx = kwargs['idx']
        except KeyError:
            pass
        try:
            assert isinstance(kwargs['initial_time'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' ClosestNextDriveCaller: <initial_time> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.initial_time = kwargs['initial_time']
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' ClosestNextDriveCaller: <initial_time> is not set, assuming 0.' + 
                '\n-------------------\n')
            self.initial_time = 0.
        
        try:
            assert isinstance(kwargs['final_time'], (Number, MBVar, str)), (
                    '\n-------------------\nERROR:' +
                    ' ClosestNextDriveCaller: <final_time> must either be a number, '
                    '\'forever\', or an MBVar' + 
                    '\n-------------------\n')
            self.final_time = kwargs['final_time']
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' ClosestNextDriveCaller: <final_time> is not set' + 
                    '\n-------------------\n')
        try:
            assert isinstance(kwargs['increment'], DriveCaller), (
                    '\n-------------------\nERROR:' +
                    ' ClosestNextDriveCaller: <increment> should be a' + 
                    ' DriveCaller instance' + 
                    '\n-------------------\n')
            self.increment = kwargs['increment']
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' ClosestNextDriveCaller: <increment> is not set' + 
                    '\n-------------------\n')
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}'.format(self.type)
        s = s + ',\n\t{}, {},'.format(self.initial_time, self.final_time)
        s = s + '\n\t# increment drive'
        if self.increment.idx < 0:
            s = s + '\n\t{}'.format(self.increment)
        else:
            s = s + '\n\treference, {}'.format(self.increment.idx)
        return s

class CosineDriveCaller(DriveCaller):
    type = 'cosine'
    def __init__(self, **kwargs):
        try:
            assert isinstance(kwargs['idx'], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' CosineDriveCaller: <idx> must either be an integer value or an MBVar' + 
                    '\n-------------------\n')
            self.idx = kwargs['idx']
        except KeyError:
            pass
        try:
            assert isinstance(kwargs['initial_time'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' CosineDriveCaller: <initial_time> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.initial_time = kwargs['initial_time']
        except KeyError:
            errprint(
                    '\n-------------------\nWARNING:' +
                    ' CosineDriveCaller: <initial_time> not set, assuming 0.' + 
                    '\n-------------------\n'
                    )
            self.initial_time = 0.
            pass
        try:
            assert isinstance(kwargs['angular_velocity'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' CosineDriveCaller: <angular_velocity> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.angular_velocity = kwargs['angular_velocity']
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' CosineDriveCaller: <angular_velocity> is required' + 
                    '\n-------------------\n'
            )
        try:
            assert isinstance(kwargs['amplitude'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' CosineDriveCaller: <amplitude> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.amplitude = kwargs['amplitude']
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' CosineDriveCaller: <amplitude> is required' + 
                    '\n-------------------\n'
            )
        try:
            assert isinstance(kwargs['number_of_cycles'], (Number, MBVar, str)), (
                    '\n-------------------\nERROR:' +
                    ' CosineDriveCaller: <number_of_cycles> must either be a number,'
                    ' one in (\'half\', \'one\', \'forever\'), or an MBVar' + 
                    '\n-------------------\n')
            self.number_of_cycles = kwargs['number_of_cycles']
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' CosineDriveCaller: <number_of_cycles> is required' + 
                    '\n-------------------\n'
            )
        try:
            assert isinstance(kwargs['initial_value'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' CosineDriveCaller: <initial_value> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.initial_value = kwargs['initial_value']
        except KeyError:
            errprint(
                    '\n-------------------\nWARNING:' +
                    ' CosineDriveCaller: <initial_value> not provided, assuming 0.' + 
                    '\n-------------------\n'
            )
            self.initial_value = 0.
            pass
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}, {}, '.format(self.type, self.initial_time)
        s = s + '{}, {}, '.format(self.angular_velocity, self.amplitude)
        s = s + '{}, {}'.format(self.number_of_cycles, self.initial_value)
        return s

class CubicDriveCaller(DriveCaller):
    type = 'cubic'
    def __init__(self, **kwargs):
        try:
            assert isinstance(kwargs['idx'], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' CubicDriveCaller: <idx> must either be an integer value or an MBVar' + 
                    '\n-------------------\n')
            self.idx = kwargs['idx']
        except KeyError:
            pass
        try:
            assert isinstance(kwargs['const_coef'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' CubicDriveCaller: <const_coef> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.const_coef = kwargs['const_coef']
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' CubicDriveCaller: <const_coef> is required' + 
                    '\n-------------------\n'
                    )
        try:
            assert isinstance(kwargs['linear_coef'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' CubicDriveCaller: <linear_coef> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.linear_coef = kwargs['linear_coef']
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' CubicDriveCaller: <linear_coef> is required' + 
                    '\n-------------------\n'
                    )
        try:
            assert isinstance(kwargs['parabolic_coef'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' CubicDriveCaller: <parabolic_coef> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.parabolic_coef = kwargs['parabolic_coef']
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' CubicDriveCaller: <parabolic_coef> is required' + 
                    '\n-------------------\n'
                    )
        try:
            assert isinstance(kwargs['cubic_coef'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' CubicDriveCaller: <cubic_coef> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.cubic_coef = kwargs['cubic_coef']
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' CubicDriveCaller: <cubic_coef> is required' + 
                    '\n-------------------\n'
                    )
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}, {}, '.format(self.type, self.const_coef)
        s = s + '{}, {}, '.format(self.linear_coef, self.parabolic_coef)
        s = s + '{}'.format(self.cubic_coef)
        return s

class DirectDriveCaller(DriveCaller):
    type = 'direct'
    def __init__(self, **kwargs):
        try:
            assert isinstance(kwargs['idx'], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' DirectDriveCaller: <idx> must either be an integer value or an MBVar' + 
                    '\n-------------------\n')
            self.idx = kwargs['idx']
        except KeyError:
            pass
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}'.format(self.type)
        return s

class DiscreteFilterDriveCaller(DriveCaller):
    type = 'discrete filter'
    def __init__(self, **kwargs):
        try:
            assert isinstance(kwargs['idx'], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' DiscreteFilterDriveCaller: <idx> must either be an integer value or an MBVar' + 
                    '\n-------------------\n')
            self.idx = kwargs['idx']
        except KeyError:
            pass
        try:
            assert isinstance(kwargs['n_a'], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' DiscreteFilterDriveCaller: <n_a> must either be an integer or an MBVar' + 
                    '\n-------------------\n')
            self.n_a = kwargs['n_a']
        except KeyError:
            errprint(
                    '\n-------------------\nWARNING:' +
                    ' DiscreteFilterDriveCaller: <n_a> is required' + 
                    '\n-------------------\n'
                    )
        try:
            assert isinstance(kwargs['a'], list), (
                    '\n-------------------\nERROR:' +
                    ' DiscreteFilterDriveCaller: <a> must be a list of' + 
                    ' numbers or MBVars' + 
                    '\n-------------------\n')
        except KeyError:
            errprint(
                    '\n-------------------\nWARNING:' +
                    ' DiscreteFilterDriveCaller: <n_a> is required' + 
                    '\n-------------------\n'
                    )
        for a_i in kwargs['a']:
            assert isinstance(a_i, (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' DiscreteFilterDriveCaller: each component of <a> must be a' + 
                    ' number or an MBVar' + 
                    '\n-------------------\n'
                )
        self.a = kwargs['a']
        try:
            assert isinstance(kwargs['b_0'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' DiscreteFilterDriveCaller: <b_0> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.b_0 = kwargs['b_0']
        except KeyError:
            errprint(
                    '\n-------------------\nWARNING:' +
                    ' DiscreteFilterDriveCaller: <b_0> is required' +
                    ' set to 0 if not needed' +
                    '\n-------------------\n'
                    )
        try:
            assert isinstance(kwargs['n_b'], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' DiscreteFilterDriveCaller: <n_b> must either be an integer or an MBVar' + 
                    '\n-------------------\n')
            self.n_b = kwargs['n_b']
        except KeyError:
            errprint(
                    '\n-------------------\nWARNING:' +
                    ' DiscreteFilterDriveCaller: <n_b> is required' + 
                    '\n-------------------\n'
                    )
        try:
            assert isinstance(kwargs['b'], list), (
                    '\n-------------------\nERROR:' +
                    ' DiscreteFilterDriveCaller: <b> must be a list of' + 
                    ' numbers or MBVars' + 
                    '\n-------------------\n')
        except KeyError:
            errprint(
                    '\n-------------------\nWARNING:' +
                    ' DiscreteFilterDriveCaller: <n_b> is required' + 
                    '\n-------------------\n'
                    )
        for b_i in kwargs['b']:
            assert isinstance(b_i, (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' DiscreteFilterDriveCaller: each component of <b> must be a' + 
                    ' number or an MBVar' + 
                    '\n-------------------\n'
                )
        self.b = kwargs['b']
        try:
            assert isinstance(kwargs['input_drive'], DriveCaller), (
                    '\n-------------------\nERROR:' +
                    ' DiscreteFilterDriveCaller: <input_drive> should be a' + 
                    ' DriveCaller instance' + 
                    '\n-------------------\n')
            self.input_drive = kwargs['input_drive']
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' DiscreteFilterDriveCaller: <input_drive> is not set' + 
                    '\n-------------------\n')
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}, '.format(self.type)
        s = s + '\n\t{}'.format(self.n_a)
        for a_i in self.a:
            s = s + ',\n\t\t{}'.format(a_i)
        s = s + ',\n\t{}'.format(self.b_0)
        s = s + ',\n\t{}'.format(self.n_b)
        for b_i in self.b:
            s = s + ',\n\t\t{}'.format(b_i)
        if self.input_drive.idx >= 0:
            s = s + ',\n\treference, {}'.format(self.input_drive.idx)
        else:
            s = s + ',\n\t{}'.format(self.input_drive)
        return s


class DofDriveCaller(DriveCaller):
    type = 'dof'
    def __init__(self, **kwargs):
        try:
            assert isinstance(kwargs['idx'], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' DofDriveCaller: <idx> must either be an integer value or an MBVar' + 
                    '\n-------------------\n'
            )
            self.idx = kwargs['idx']
        except KeyError:
            pass
        try:
            assert(isinstance(kwargs['driving_dof'], NodeDof)), (
                    '\n-------------------\nERROR:' +
                    ' DofDriveCaller: <driving_dof> must be a NodeDof' + 
                    '\n-------------------\n'
            )
            self.driving_dof = kwargs['driving_dof']
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' DofDriveCaller: <driving_dof> must be provided' + 
                    '\n-------------------\n'
            )
        try:
            assert(isinstance(kwargs['func_drive'], DriveCaller)), (
                    '\n-------------------\nERROR:' +
                    ' DofDriveCaller: <func_drive> must be a DriveCaller' + 
                    '\n-------------------\n'
            )
            self.func_drive = kwargs['func_drive']
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' DofDriveCaller: <func_drive> must be provided' + 
                    '\n-------------------\n'
            )
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}'.format(self.idx)
        s = s + ', {}'.format(self.type)
        s = s + ',\n\t{}'.format(self.driving_dof)
        s = s + ',\n\t{}'.format(self.func_drive)
        return s

class DoubleRampDriveCaller(DriveCaller):
    type = 'double ramp'
    def __init__(self, **kwargs):
        try:
            assert isinstance(kwargs['idx'], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' DoubleRampDriveCaller: <idx> must either be an integer value or an MBVar' + 
                    '\n-------------------\n')
            self.idx = kwargs['idx']
        except KeyError:
            pass
        try:
            assert isinstance(kwargs['a_slope'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' DoubleRampDriveCaller: <a_slope> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.a_slope = kwargs['a_slope']
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' DoubleRampDriveCaller: <a_slope> must be provided' + 
                '\n-------------------\n')
        try:
            assert isinstance(kwargs['a_initial_time'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' DoubleRampDriveCaller: <a_initial_time> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.a_initial_time = kwargs['a_initial_time']
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' DoubleRampDriveCaller: <a_initial_time> is not set, assuming 0.' + 
                '\n-------------------\n')
            self.a_initial_time = 0.
            pass
        try:
            assert isinstance(kwargs['a_final_time'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' DoubleRampDriveCaller: <a_final_time> must either be a number'
                    ' or an MBVar' + 
                    '\n-------------------\n')
            self.a_final_time = kwargs['a_final_time']
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' DoubleRampDriveCaller: <a_final_time> must be provided' + 
                    '\n-------------------\n')
        try:
            assert isinstance(kwargs['d_slope'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' DoubleRampDriveCaller: <d_slope> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.d_slope = kwargs['d_slope']
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' DoubleRampDriveCaller: <d_slope> must be provided' + 
                '\n-------------------\n')
        try:
            assert isinstance(kwargs['d_initial_time'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' DoubleRampDriveCaller: <d_initial_time> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.d_initial_time = kwargs['d_initial_time']
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' DoubleRampDriveCaller: <d_initial_time> must be provided' + 
                '\n-------------------\n')
        try:
            assert isinstance(kwargs['d_final_time'], (Number, MBVar, str)), (
                    '\n-------------------\nERROR:' +
                    ' DoubleRampDriveCaller: <a_final_time> must either be a number,'
                    ' an MBVar, or \'forever\'' + 
                    '\n-------------------\n')
            self.d_final_time = kwargs['d_final_time']
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' DoubleRampDriveCaller: <d_final_time> is not set' + 
                    '\n-------------------\n')
        try:
            assert isinstance(kwargs['initial_value'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' DoubleRampDriveCaller: <initial_value> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.initial_value = kwargs['initial_value']
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' DoubleRampDriveCaller: <initial_value> must be provided' + 
                '\n-------------------\n') # Why is it not assumed to be zero?
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}'.format(self.type)
        s = s + ',\n\t{}, {}, {}'.format(self.a_slope, self.a_initial_time, self.a_final_time)
        s = s + ',\n\t{}, {}, {}'.format(self.d_slope, self.d_initial_time, self.d_final_time)
        s = s + ',\n\t{}'.format(self.initial_value)
        return s

class DoubleStepDriveCaller(DriveCaller):
    type = 'double step'
    def __init__(self, **kwargs):
        try:
            assert isinstance(kwargs['idx'], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' DoubleStepDriveCaller: <idx> must either be an integer value or an MBVar' + 
                    '\n-------------------\n')
            self.idx = kwargs['idx']
        except KeyError:
            pass
        try:
            assert isinstance(kwargs['initial_time'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' DoubleStepDriveCaller: <initial_time> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.initial_time = kwargs['initial_time']
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' DoubleStepDriveCaller: <initial_time> not set, assuming 0.' + 
                '\n-------------------\n')
            self.initial_time = 0.
            pass
        try:
            assert isinstance(kwargs['final_time'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' DoubleStepDriveCaller: <final_time> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.final_time = kwargs['final_time']
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' DoubleStepDriveCaller: <final_time> is not set' + 
                '\n-------------------\n')
        try:
            assert isinstance(kwargs['step_value'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' DoubleStepDriveCaller: <step_value> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.step_value = kwargs['step_value']
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' DoubleStepDriveCaller: <step_value> is not set' + 
                '\n-------------------\n')
        try:
            assert isinstance(kwargs['initial_value'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' DoubleStepDriveCaller: <initial_value> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.initial_value = kwargs['initial_value']
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' DoubleStepDriveCaller: <initial_value> is not set, assuming 0.' + 
                '\n-------------------\n')
            self.initial_value = 0.
            pass
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}'.format(self.type)
        s = s + ',\n\t{}, {}'.format(self.initial_time, self.final_time)
        s = s + ',\n\t{}, {}'.format(self.step_value, self.initial_value)
        return s


class DriveDriveCaller(DriveCaller):
    type = 'drive'
    def __init__(self, **kwargs):
        try:
            assert isinstance(kwargs['idx'], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' DriveDriveCaller: <idx> must either be an integer value or an MBVar' + 
                    '\n-------------------\n')
            self.idx = kwargs['idx']
        except KeyError:
            pass
        try:
            assert isinstance(kwargs['drive_caller1'], DriveCaller), (
                    '\n-------------------\nERROR:' +
                    ' DriveDriveCaller: <drive_caller1> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.drive_caller1 = kwargs['drive_caller1']
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' DriveDriveCaller: <drive_caller1> not set' + 
                '\n-------------------\n')
        try:
            assert isinstance(kwargs['drive_caller2'], DriveCaller), (
                    '\n-------------------\nERROR:' +
                    ' DriveDriveCaller: <drive_caller2> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.drive_caller2 = kwargs['drive_caller2']
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' DriveDriveCaller: <drive_caller1> not set' + 
                '\n-------------------\n')
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}'.format(self.type)
        if self.drive_caller1.idx < 0:
            s = s + ',\n\t{}'.format(self.drive_caller1)
        else:
            s = s + ',\n\treference, {}'.format(self.drive_caller1.idx)
        if self.drive_caller2.idx < 0:
            s = s + ',\n\t{}'.format(self.drive_caller2)
        else:
            s = s + ',\n\treference, {}'.format(self.drive_caller2.idx)
        return s


class ElementDriveCaller(DriveCaller):
    type = 'element'
    def __init__(self, **kwargs):
        try:
            assert isinstance(kwargs['idx'], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' ElementDriveCaller: <idx> must either be an integer value or an MBVar' + 
                    '\n-------------------\n')
            self.idx = kwargs['idx']
        except KeyError:
            pass
        try:
            assert isinstance(kwargs['element'], Element), (
                    '\n-------------------\nERROR:' +
                    ' ElementDriveCaller: <element> must be an instance of Element' + 
                    '\n-------------------\n')
            self.element = kwargs['element']
        except KeyError:
            (
                '\n-------------------\nERROR:' +
                ' ElementDriveCaller: <element> not set' + 
                '\n-------------------\n')
        try:
            assert isinstance(kwargs['private_data'], str), (
                    '\n-------------------\nERROR:' +
                    ' ElementDriveCaller: <private_data> must be a string' + 
                    '\n-------------------\n')
            self.private_data = kwargs['private_data']
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' ElementDriveCaller: <private_data> is not set' + 
                '\n-------------------\n')
        try:
            assert isinstance(kwargs['func_drive'], (DriveCaller, str)), (
                    '\n-------------------\nERROR:' +
                    ' ElementDriveCaller: <func_drive> must either be a' +
                    ' DriveCaller or \'direct\'' + 
                    '\n-------------------\n')
            if isinstance(kwargs['func_drive'], str) and kwargs['func_drive'] != 'direct':
                raise ValueError(
                    '\n-------------------\nERROR:' +
                    ' ElementDriveCaller: <func_drive> must either be a' +
                    ' DriveCaller or \'direct\'' + 
                    '\n-------------------\n'
                    )
            self.func_drive = kwargs['func_drive']
        except KeyError:
            (
                '\n-------------------\nERROR:' +
                ' ElementDriveCaller: <func_drive> is not set' + 
                '\n-------------------\n')
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}'.format(self.type)
        s = s + ', {}, {}'.format(self.element.idx, self.element.type)
        s = s + ', string, \"{}\"'.format(self.private_data)
        s = s + ', {}'.format(self.func_drive)
        return s


class ExponentialDriveCaller(DriveCaller):
    type = 'exponential'
    def __init__(self, **kwargs):
        try:
            arg = 'idx'
            assert isinstance(kwargs[arg], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' {}: <{}> must either be'.format(self.__class__.__name__, arg) + 
                    ' an integer value or an MBVar' + 
                    '\n-------------------\n')
            self.idx = kwargs[arg]
        except KeyError:
            pass
        try:
            arg = 'amplitude_value'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' {}: <{}> must either be'.format(self.__class__.__name__, arg) +
                    ' a number of an MBVar' + 
                    '\n-------------------\n')
            self.amplitude_value = kwargs[arg]
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' {}: <{}> not set'.format(self.__class__.__name__, arg) + 
                '\n-------------------\n')
        try:
            arg = 'time_constant_value'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' {}: <{}> must either be'.format(self.__class__.__name__, arg) +
                    ' a number of an MBVar' + 
                    '\n-------------------\n')
            self.time_constant_value = kwargs[arg]
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' {}: <{}> not set'.format(self.__class__.__name__, arg) + 
                '\n-------------------\n')
        try:
            arg = 'initial_time'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' {}: <{}> must either be'.format(self.__class__.__name__, arg) +
                    ' a number of an MBVar' + 
                    '\n-------------------\n')
            self.initial_time = kwargs[arg]
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' {}: <{}> not set, assuming 0.'.format(self.__class__.__name__, arg) + 
                '\n-------------------\n')
            self.initial_time = 0.
            pass
        try:
            arg = 'initial_value'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' {}: <{}> must either be'.format(self.__class__.__name__, arg) +
                    ' a number of an MBVar' + 
                    '\n-------------------\n')
            self.initial_value = kwargs[arg]
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' {}: <{}> not set, assuming 0.'.format(self.__class__.__name__, arg) + 
                '\n-------------------\n')
            self.initial_value = 0.
            pass
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}'.format(self.type)
        s = s + ', {}, {}, {}, {}'.format(
                    self.amplitude_value, 
                    self.time_constant_value,
                    self.initial_time,
                    self.initial_value
                    )
        return s


class FileDriveDrive(DriveCaller):
    # TODO: needs FileDrive before
    pass


class FourierSeriesDrive(DriveCaller):
    type = 'fourier series'
    def __init__(self, **kwargs):
        try:
            assert isinstance(kwargs['idx'], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' FourierSeriesDrive: <idx> must either be an integer value or an MBVar' + 
                    '\n-------------------\n')
            self.idx = kwargs['idx']
        except KeyError:
            pass
        try:
            arg = 'initial_time'
            assert isinstance(kwargs[arg], (MBVar, Number)), (
                    '\n-------------------\nERROR:' +
                    ' {}: <{}> must be'.format(self.__class__.__name__, arg) +
                    ' a number or an MBVar' + 
                    '\n-------------------\n')
            if isinstance(kwargs[arg], MBVar) and ('real' not in kwargs[arg].var_type):
                raise TypeError(
                    '\n-------------------\nERROR:' +
                    ' {}: <{}> must be'.format(self.__class__.__name__, arg) +
                    ' an MBVar of type real' + 
                    '\n-------------------\n'
                )
            self.initial_time= kwargs[arg]
        except KeyError:
            pass
        try:
            arg = 'angular_velocity'
            assert isinstance(kwargs[arg], (MBVar, Number)), (
                    '\n-------------------\nERROR:' +
                    ' {}: <{}> must be'.format(self.__class__.__name__, arg) +
                    ' a number or an MBVar' + 
                    '\n-------------------\n')
            if isinstance(kwargs[arg], MBVar) and ('real' not in kwargs[arg].var_type):
                raise TypeError(
                    '\n-------------------\nERROR:' +
                    ' {}: <{}> must be'.format(self.__class__.__name__, arg) +
                    ' an MBVar of type real' + 
                    '\n-------------------\n'
                )
            self.angular_velocity = kwargs[arg]
        except KeyError:
            pass
        try:
            arg = 'number_of_terms'
            assert isinstance(kwargs[arg], (MBVar, Integral)), (
                    '\n-------------------\nERROR:' +
                    ' {}: <{}> must be'.format(self.__class__.__name__, arg) +
                    ' a number or an MBVar' + 
                    '\n-------------------\n')
            if isinstance(kwargs[arg], MBVar) and ('integer' not in kwargs[arg].var_type):
                raise TypeError(
                    '\n-------------------\nERROR:' +
                    ' {}: <{}> must be'.format(self.__class__.__name__, arg) +
                    ' an MBVar of type integer' + 
                    '\n-------------------\n'
                )
            self.number_of_terms = kwargs[arg]
        except KeyError:
            pass
        try:
            arg = 'number_of_cycles'
            assert isinstance(kwargs[arg], (MBVar, Integral, str)), (
                    '\n-------------------\nERROR:' +
                    ' {}: <{}> must be'.format(self.__class__.__name__, arg) +
                    ' a number or an MBVar' + 
                    '\n-------------------\n')
            if isinstance(kwargs[arg], MBVar) and kwargs[arg].var_type == 'string':
                if kwargs[arg] not in ('one', 'forever'):
                    raise ValueError(
                        '\n-------------------\nERROR:' +
                        ' {}: <{}> must be'.format(self.__class__.__name__, arg) +
                        ' either \'one\' or \'forever\', if of type string' + 
                        '\n-------------------\n'
                        )
            self.number_of_cycles = kwargs[arg]
        except KeyError:
            pass
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}'.format(self.type)
        s = s + ', {}, {}, {}'.format(
                    self.initial_time, 
                    self.angular_velocity,
                    self.number_of_terms
                    )
        s = s + ',\n\t {}'.format(self.coefs)
        return s

class FrequencySweepDriveCaller(DriveCaller):
    type = 'frequency sweep'
    def __init__(self, **kwargs):
        try:
            assert isinstance(kwargs['idx'], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' FrequencySweepDriveCaller: <idx> must either be an integer value or an MBVar' + 
                    '\n-------------------\n'
            )
            self.idx = kwargs['idx']
        except KeyError:
            pass
        try:
            assert isinstance(kwargs['initial_time'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' FrequencySweepDriveCaller: <initial_time> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.initial_time = kwargs['initial_time']
        except KeyError:
            errprint(
                    '\n-------------------\nWARNING:' +
                    ' FrequencySweepDriveCaller: <initial_time> not set, assuming 0.' + 
                    '\n-------------------\n'
                    )
            self.initial_time = 0.
            pass
        try:
            assert(isinstance(kwargs['angular_velocity_drive'], DriveCaller)), (
                    '\n-------------------\nERROR:' +
                    ' FrequencySweepDriveCaller: <angular_velocity_drive> must be a DriveCaller' + 
                    '\n-------------------\n'
            )
            self.angular_velocity_drive = kwargs['angular_velocity_drive']
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' FrequencySweepDriveCaller: <angular_velocity_drive> must be provided' + 
                    '\n-------------------\n'
            )
        try:
            assert(isinstance(kwargs['amplitude_drive'], DriveCaller)), (
                    '\n-------------------\nERROR:' +
                    ' FrequencySweepDriveCaller: <amplitude_drive> must be a DriveCaller' + 
                    '\n-------------------\n'
            )
            self.amplitude_drive = kwargs['amplitude_drive']
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' FrequencySweepDriveCaller: <amplitude_drive> must be provided' + 
                    '\n-------------------\n'
            )
        try:
            assert isinstance(kwargs['initial_value'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' FrequencySweepDriveCaller: <initial_value> must either be a number or an MBVar' + 
                    '\n-------------------\n'
            )
            self.initial_value = kwargs['initial_value']
        except KeyError:
            errprint(
                    '\n-------------------\nWARNING:' +
                    ' FrequencySweepDriveCaller: <initial_value> not provided, assuming 0.' + 
                    '\n-------------------\n'
            )
            self.initial_value = 0.
            pass
        try:
            assert isinstance(kwargs['final_time'], (Number, MBVar, str)), (
                    '\n-------------------\nERROR:' +
                    ' FrequencySweepDriveCaller: <final_time> must either be a number, '
                    '\'forever\', or an MBVar' + 
                    '\n-------------------\n'
            )
            self.final_time = kwargs['final_time']
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' FrequencySweepDriveCaller: <final_time> is not set' + 
                    '\n-------------------\n'
            )
        try:
            assert isinstance(kwargs['final_value'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' FrequencySweepDriveCaller: <final_value> must either be a number or an MBVar' + 
                    '\n-------------------\n'
            )
            self.final_value = kwargs['final_value']
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' FrequencySweepDriveCaller: <final_value> is not set.' + 
                    '\n-------------------\n'
            )
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}'.format(self.type)
        s = s + ', {}'.format(self.initial_time)
        if self.angular_velocity_drive.idx < 0:
            s = s + ',\n\t{}'.format(self.angular_velocity_drive)
        else:
            s = s + ',\n\treference, {}'.format(self.angular_velocity_drive.idx)
        if self.amplitude_drive.idx < 0:
            s = s + ',\n\t{}'.format(self.amplitude_drive)
        else:
            s = s + ',\n\treference, {}'.format(self.amplitude_drive.idx)
        s = s + '\n{}, {}'.format(self.initial_value, self.final_time)
        s = s + ', {}'.format(self.final_value)
        return s

class GiNaCDriveCaller(DriveCaller):
    type = 'ginac'
    def __init__(self, **kwargs):
        try:
            arg = 'idx'
            assert isinstance(kwargs[arg], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' {}: <{}> must either be'.format(self.__class__.__name__, arg) + 
                    ' an integer value or an MBVar' + 
                    '\n-------------------\n')
            self.idx = kwargs[arg]
        except KeyError:
            pass
        try:
            arg = 'expression'
            assert isinstance(kwargs[arg], (MBVar, str)), (
                    '\n-------------------\nERROR:' +
                    ' {}: <{}> must be'.format(self.__class__.__name__, arg) +
                    ' a string or an MBVar' + 
                    '\n-------------------\n')
            if isinstance(kwargs[arg], MBVar) and ('string' not in kwargs[arg].var_type):
                raise TypeError(
                    '\n-------------------\nERROR:' +
                    ' {}: <{}> must be'.format(self.__class__.__name__, arg) +
                    ' an MBVar of type string' + 
                    '\n-------------------\n'
                )
            self.expression = kwargs[arg]
        except KeyError:
                errprint(
                '\n-------------------\nERROR' +
                ' {}: <{}> not set'.format(self.__class__.__name__, arg) + 
                '\n-------------------\n'
                )
        try:
            arg = 'symbol'
            assert isinstance(kwargs[arg], (MBVar, str)), (
                    '\n-------------------\nERROR:' +
                    ' {}: <{}> must be'.format(self.__class__.__name__, arg) +
                    ' a string or an MBVar' + 
                    '\n-------------------\n')
            if isinstance (kwargs[arg], MBVar) and ('string' not in kwargs[arg].var_type):
                raise TypeError(
                    '\n-------------------\nERROR:' +
                    ' {}: <{}> must be'.format(self.__class__.__name__, arg) +
                    ' an MBVar of type string' + 
                    '\n-------------------\n'
                )
            self.symbol = kwargs[arg]
        except KeyError:
            pass
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}'.format(self.type)
        try:
            if isinstance(self.symbol, MBVar):
                s = s + ', symbol, {}'.format(self.symbol)
            else:
                s = s + ', symbol, \"{}\"'.format(self.symbol)
        except AttributeError:
            pass
        if isinstance(self.expression, MBVar):
            s = s + ', {}'.format(self.expression)
        else:
            s = s + ', \"{}\"'.format(self.expression)
        return s
    pass


class LinearDriveCaller(DriveCaller):
    type = 'linear'
    def __init__(self, **kwargs):
        try:
            assert isinstance(kwargs['idx'], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' LinearDriveCaller: <idx> must either be an integer value or an MBVar' + 
                    '\n-------------------\n')
            self.idx = kwargs['idx']
        except KeyError:
            pass
        try:
            assert isinstance(kwargs['const_coef'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' LinearDriveCaller: <const_coef> must either be a number of an MBVar' + 
                    '\n-------------------\n')
            self.const_coef = kwargs['const_coef']
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' LinearDriveCaller: <const_coef> not set' + 
                '\n-------------------\n')
        try:
            assert isinstance(kwargs['slope_coef'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' LinearDriveCaller: <slope_coef> must either be a number of an MBVar' + 
                    '\n-------------------\n')
            self.slope_coef = kwargs['slope_coef']
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' LinearDriveCaller: <slope_coef> not set' + 
                '\n-------------------\n')
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}'.format(self.type)
        s = s + ', {}, {}'.format(self.const_coef, self.slope_coef)
        return s
    
class SineDriveCaller(DriveCaller):
    type = 'sine'
    def __init__(self, **kwargs):
        try:
            assert isinstance(kwargs['idx'], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' SineDriveCaller: <idx> must either be an integer value or an MBVar' + 
                    '\n-------------------\n'
            )
            self.idx = kwargs['idx']
        except KeyError:
            pass
        try:
            assert isinstance(kwargs['initial_time'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' SineDriveCaller: <initial_time> must either be a number or an MBVar' + 
                    '\n-------------------\n'
            )
            self.initial_time = kwargs['initial_time']
        except KeyError:
            errprint(
                    '\n-------------------\nWARNING:' +
                    ' SineDriveCaller: <initial_time> not set, assuming 0.' + 
                    '\n-------------------\n'
            )
            self.initial_time = 0.
            pass
        try:
            assert isinstance(kwargs['angular_velocity'], (Number, MBVar, expression)), (
                    '\n-------------------\nERROR:' +
                    ' SineDriveCaller: <angular_velocity> must be a number, MBVar, or expression' + 
                    '\n-------------------\n'
            )
            self.angular_velocity = kwargs['angular_velocity']
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' SineDriveCaller: <angular_velocity> is required' + 
                    '\n-------------------\n'
            )
        try:
            assert isinstance(kwargs['amplitude'], (Number, MBVar, expression)), (
                    '\n-------------------\nERROR:' +
                    ' SineDriveCaller: <amplitude> must be a number, MBVar, or expression' + 
                    '\n-------------------\n'
            )
            self.amplitude = kwargs['amplitude']
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' SineDriveCaller: <amplitude> is required' + 
                    '\n-------------------\n'
            )
        try:
            assert isinstance(kwargs['number_of_cycles'], (Number, MBVar, str)), (
                    '\n-------------------\nERROR:' +
                    ' SineDriveCaller: <number_of_cycles> must either be a number,'
                    ' one in (\'half\', \'one\', \'forever\'), or an MBVar' + 
                    '\n-------------------\n')
            self.number_of_cycles = kwargs['number_of_cycles']
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' SineDriveCaller: <number_of_cycles> is required' + 
                    '\n-------------------\n'
            )
        try:
            assert isinstance(kwargs['initial_value'], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' SineDriveCaller: <initial_value> must either be a number or an MBVar' + 
                    '\n-------------------\n'
            )
            self.initial_value = kwargs['initial_value']
        except KeyError:
            errprint(
                    '\n-------------------\nWARNING:' +
                    ' SineDriveCaller: <initial_value> not provided, assuming 0.' + 
                    '\n-------------------\n'
            )
            self.initial_value = 0.
            pass
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}, {}, '.format(self.type, self.initial_time)
        s = s + '{}, {}, '.format(self.angular_velocity, self.amplitude)
        s = s + '{}, {}'.format(self.number_of_cycles, self.initial_value)
        return s
        
class MeterDriveCaller(DriveCaller):
    type = 'meter'
    def __init__(self, **kwargs):
        try:
            arg = 'idx'
            assert isinstance(kwargs[arg], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' MeterDriveCaller: <idx> must either be an integer value or an MBVar' + 
                    '\n-------------------\n')
            self.idx = kwargs['idx']
        except KeyError:
            pass
        try:
            arg = 'initial_time'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' MeterDriveCaller: <initial_time> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.initial_time = kwargs[arg]
        except KeyError:
            errprint(
                    '\n-------------------\nWARNING:' +
                    ' MeterDriveCaller: <initial_time> not set, assuming 0.' + 
                    '\n-------------------\n'
            )
            self.initial_time = 0.
        try:
            arg = 'final_time'
            assert isinstance(kwargs[arg], (Number, MBVar, str)), (
                    '\n-------------------\nERROR:' +
                    ' MeterDriveCaller: <final_time> must either be a number, '
                    '\'forever\', or an MBVar' + 
                    '\n-------------------\n')
            self.final_time = kwargs[arg]
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' MeterDriveCaller: <final_time> is not set' + 
                    '\n-------------------\n')
        try:
            arg = 'steps_between_spikes'
            assert isinstance(kwargs[arg], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' MeterDriveCaller: <steps_between_spikes> must either be an integer value or an MBVar' + 
                    '\n-------------------\n')
            self.steps = kwargs[arg]
        except KeyError:
            pass
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}, {}, '.format(self.type, self.initial_time)
        s = s + '{}'.format(self.final_time)
        try:
            s = s + ', steps, {}'.format(self.steps_between_spikes)
        except AttributeError:
            pass
        return s
    
class MultDriveCaller(DriveCaller):
    type = 'mult'
    def __init__(self, **kwargs):
        try:
            arg = 'idx'
            assert isinstance(kwargs[arg], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' MultDriveCaller: <idx> must either be an integer value or an MBVar' + 
                    '\n-------------------\n')
            self.idx = kwargs['idx']
        except KeyError:
            pass
        try:
            arg = 'drive_1'
            assert(isinstance(kwargs[arg], DriveCaller)), (
                    '\n-------------------\nERROR:' +
                    ' MultDriveCaller: <drive_1> must be a DriveCaller' + 
                    '\n-------------------\n')
            self.drive_1 = kwargs[arg]
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' MultDriveCaller: <drive_1> must be provided' + 
                    '\n-------------------\n'
            )
        try:
            arg = 'drive_2'
            assert(isinstance(kwargs[arg], DriveCaller)), (
                    '\n-------------------\nERROR:' +
                    ' MultDriveCaller: <drive_2> must be a DriveCaller' + 
                    '\n-------------------\n')
            self.drive_2 = kwargs[arg]
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' MultDriveCaller: <drive_2> must be provided' + 
                    '\n-------------------\n'
            )
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}'.format(self.type)
        if self.drive_1.idx < 0:
            s = s + ',\n\t{}'.format(self.drive_1)
        else:
            s = s + ',\n\treference, {}'.format(self.drive_1.idx)
        if self.drive_2.idx < 0:
            s = s + ',\n\t{}'.format(self.drive_2)
        else:
            s = s + ',\n\treference, {}'.format(self.drive_2.idx)
        return s
    
class NullDriveCaller(DriveCaller):
    type = 'null'
    def __init__(self, **kwargs):
        try:
            arg = 'idx'
            assert isinstance(kwargs[arg], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' NullDriveCaller: <idx> must either be an integer value or an MBVar' + 
                    '\n-------------------\n')
            self.idx = kwargs['idx']
        except KeyError:
            pass
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}'.format(self.type)
        return s
    
class ParabolicDriveCaller(DriveCaller):
    type = 'parabolic'
    def __init__(self, **kwargs):
        try:
            arg = 'idx'
            assert isinstance(kwargs[arg], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' ParabolicDriveCaller: <idx> must either be an integer value or an MBVar' + 
                    '\n-------------------\n')
            self.idx = kwargs[arg]
        except KeyError:
            pass
        try:
            arg = 'const_coef'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' ParabolicDriveCaller: <const_coef> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.const_coef = kwargs[arg]
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' ParabolicDriveCaller: <const_coef> is required' + 
                    '\n-------------------\n'
                    )
        try:
            arg = 'liner_coef'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' ParabolicDriveCaller: <linear_coef> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.linear_coef = kwargs[arg]
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' ParabolicDriveCaller: <linear_coef> is required' + 
                    '\n-------------------\n'
                    )
        try:
            arg = 'parabolic_coef'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' ParabolicDriveCaller: <parabolic_coef> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.parabolic_coef = kwargs[arg]
        except KeyError:
            errprint(
                    '\n-------------------\nERROR:' +
                    ' ParabolicDriveCaller: <parabolic_coef> is required' + 
                    '\n-------------------\n'
                    )
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}, {}, '.format(self.type, self.const_coef)
        s = s + '{}, {}'.format(self.linear_coef, self.parabolic_coef)
        return s
    
class PeriodicDriveCaller(DriveCaller):
    type = 'periodic'
    def __init__(self, **kwargs):
        try:
            arg = 'idx'
            assert isinstance(kwargs[arg], (Integral, MBVar)), (
                '\n-------------------\nERROR:' +
                ' PeriodicDriveCaller: <idx> must either be an integer value or an MBVar' +
                '\n-------------------\n'
            )
            self.idx = kwargs[arg]
        except KeyError:
            pass
        try:
            arg = 'initial_time'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                '\n-------------------\nERROR:' +
                ' PeriodicDriveCaller: <initial_time> must either be a number or an MBVar' +
                '\n-------------------\n'
            )
            self.initial_time = kwargs[arg]
        except KeyError:
            errprint(
                '\n-------------------\nWARNING:' +
                ' PeriodicDriveCaller: <initial_time> not set, assuming 0.' +
                '\n-------------------\n'
            )
            self.initial_time = 0.
        try:
            arg = 'period'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                '\n-------------------\nERROR:' +
                ' PeriodicDriveCaller: <period> must either be a number or an MBVar' +
                '\n-------------------\n'
            )
            self.period = kwargs[arg]
        except KeyError:
            errprint(
                '\n-------------------\nERROR:' +
                ' PeriodicDriveCaller: <period> is required' +
                '\n-------------------\n'
            )
        try:
            arg = 'func_drive'
            assert isinstance(kwargs[arg], DriveCaller), (
                '\n-------------------\nERROR:' +
                ' PeriodicDriveCaller: <func_drive> must be a DriveCaller' +
                '\n-------------------\n'
            )
            self.func_drive = kwargs[arg]
        except KeyError:
            errprint(
                '\n-------------------\nERROR:' +
                ' PeriodicDriveCaller: <func_drive> must be provided' +
                '\n-------------------\n'
            )
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}'.format(self.type)
        s = s + ', {}, {}, {}'.format(self.initial_time, self.period, self.func_drive)
        return s

class NodeDriveCaller(DriveCaller):
    type = 'node'
    def __init__(self, **kwargs):
        try:
            arg = 'idx'
            assert isinstance(kwargs[arg], (Integral, MBVar)), (
                '\n-------------------\nERROR:' +
                ' NodeDriveCaller: <idx> must either be an integer value or an MBVar' +
                '\n-------------------\n'
            )
            self.idx = kwargs[arg]
        except KeyError:
            pass
        try:
            arg = 'node'
            assert isinstance(kwargs[arg], Node), (
                '\n-------------------\nERROR:' +
                ' NodeDriveCaller: <node> must be an instance of Node' +
                '\n-------------------\n'
            )
            self.node = kwargs[arg]
        except KeyError:
            (
                '\n-------------------\nERROR:' +
                ' NodeDriveCaller: <node> not set' +
                '\n-------------------\n'
            )
        try:
            arg = 'private_data'
            assert isinstance(kwargs[arg], str), (
                '\n-------------------\nERROR:' +
                ' NodeDriveCaller: <private_data> must be a string' +
                '\n-------------------\n'
            )
            self.private_data = kwargs[arg]
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' NodeDriveCaller: <private_data> is not set' +
                '\n-------------------\n'
            )
        try:
            arg = 'func_drive'
            assert isinstance(kwargs[arg], (DriveCaller, str)), (
                '\n-------------------\nERROR:' +
                ' NodeDriveCaller: <func_drive> must either be a' +
                ' DriveCaller or \'direct\'' +
                '\n-------------------\n'
            )
            if isinstance(kwargs[arg], str) and kwargs[arg] != 'direct':
                raise ValueError(
                    '\n-------------------\nERROR:' +
                    ' NodeDriveCaller: <func_drive> must either be a' +
                    ' DriveCaller or \'direct\'' +
                    '\n-------------------\n'
                )
            self.func_drive = kwargs[arg]
        except KeyError:
            (
                '\n-------------------\nERROR:' +
                ' NodeDriveCaller: <func_drive> is not set' +
                '\n-------------------\n'
            )
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}'.format(self.type)
        s = s + ', {}, {}'.format(self.node.idx, self.node.type)
        s = s + ', string, \"{}\"'.format(self.private_data)
        s = s + ', {}'.format(self.func_drive)
        return s
        
class RampDriveCaller(DriveCaller):
    type = 'ramp'
    def __init__(self, **kwargs):
        try:
            arg = 'idx'
            assert isinstance(kwargs[arg], (Integral, MBVar)), (
                '\n-------------------\nERROR:' +
                ' RampDriveCaller: <idx> must either be an integer value or an MBVar' +
                '\n-------------------\n'
            )
            self.idx = kwargs[arg]
        except KeyError:
            pass
        try:
            arg = 'slope'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                '\n-------------------\nERROR:' +
                ' RampDriveCaller: <slope> must either be a number or an MBVar' +
                '\n-------------------\n'
            )
            self.slope = kwargs[arg]
        except KeyError:
            errprint(
                '\n-------------------\nERROR:' +
                ' RampDriveCaller: <slope> is required' +
                '\n-------------------\n'
            )
        try:
            arg = 'initial_time'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                '\n-------------------\nERROR:' +
                ' RampDriveCaller: <initial_time> must either be a number or an MBVar' +
                '\n-------------------\n'
            )
            self.initial_time = kwargs[arg]
        except KeyError:
            errprint(
                '\n-------------------\nWARNING:' +
                ' RampDriveCaller: <initial_time> not set, assuming 0.' +
                '\n-------------------\n'
            )
            self.initial_time = 0.
        try:
            arg = 'final_time'
            assert isinstance(kwargs[arg], (Number, MBVar, str)), (
                '\n-------------------\nERROR:' +
                ' RampDriveCaller: <final_time> must either be a number, '
                '\'forever\', or an MBVar' + 
                '\n-------------------\n')
            self.final_time = kwargs[arg]
        except KeyError:
            errprint(
                '\n-------------------\nERROR:' +
                ' RampDriveCaller: <final_time> is not set' + 
                '\n-------------------\n')
        try:
            arg = 'initial_value'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                '\n-------------------\nERROR:' +
                ' RampDriveCaller: <initial_value> must either be a number or an MBVar' + 
                '\n-------------------\n'
            )
            self.initial_value = kwargs[arg]
        except KeyError:
            errprint(
                '\n-------------------\nWARNING:' +
                ' RampDriveCaller: <initial_value> not provided, assuming 0.' + 
                '\n-------------------\n'
            )
            self.initial_value = 0.        
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}'.format(self.type)
        s = s + ', {}, {}'.format(self.slope, self.initial_time)
        s = s + ', {}, {}'.format(self.final_time, self.initial_value)
        return s

class RandomDriveCaller(DriveCaller):
    type = 'random'
    def __init__(self, **kwargs):
        try:
            arg = 'idx'
            assert isinstance(kwargs[arg], (Integral, MBVar)), (
                '\n-------------------\nERROR:' +
                ' RandomDriveCaller: <idx> must either be an integer value or an MBVar' +
                '\n-------------------\n'
            )
            self.idx = kwargs[arg]
        except KeyError:
            pass
        try:
            arg = 'amplitude_value'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                '\n-------------------\nERROR:' +
                ' RandomDriveCaller: <amplitude_value> must either be a number or an MBVar' +
                '\n-------------------\n'
            )
            self.amplitude_value = kwargs[arg]
        except KeyError:
            errprint(
                '\n-------------------\nERROR:' +
                ' RandomDriveCaller: <amplitude_value> is required' +
                '\n-------------------\n'
            )
        try:
            arg = 'mean_value'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                '\n-------------------\nERROR:' +
                ' RandomDriveCaller: <mean_value> must either be a number or an MBVar' +
                '\n-------------------\n'
            )
            self.mean_value = kwargs[arg]
        except KeyError:
            errprint(
                '\n-------------------\nERROR:' +
                ' RandomDriveCaller: <mean_value> is required' +
                '\n-------------------\n'
            )
        try:
            arg = 'initial_time'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                '\n-------------------\nERROR:' +
                ' RandomDriveCaller: <initial_time> must either be a number or an MBVar' +
                '\n-------------------\n'
            )
            self.initial_time = kwargs[arg]
        except KeyError:
            errprint(
                '\n-------------------\nWARNING:' +
                ' RandomDriveCaller: <initial_time> not set, assuming 0.' +
                '\n-------------------\n'
            )
            self.initial_time = 0.
        try:
            arg = 'final_time'
            assert isinstance(kwargs[arg], (Number, MBVar, str)), (
                '\n-------------------\nERROR:' +
                ' RandomDriveCaller: <final_time> must either be a number, '
                '\'forever\', or an MBVar' + 
                '\n-------------------\n'
            )
            self.final_time = kwargs[arg]
        except KeyError:
            errprint(
                '\n-------------------\nERROR:' +
                ' RandomDriveCaller: <final_time> is required' +
                '\n-------------------\n'
            )
        try:
            arg = 'steps_to_hold_value'
            assert isinstance(kwargs[arg], (Integral, MBVar)), (
                '\n-------------------\nERROR:' +
                ' RandomDriveCaller: <steps_to_hold_value> must either be an integer value or an MBVar' +
                '\n-------------------\n'
            )
            self.steps_to_hold_value = kwargs[arg]
        except KeyError:
            pass  
        try:
            arg = 'seed_value'
            assert isinstance(kwargs[arg], (Integral, MBVar)), (
                '\n-------------------\nERROR:' +
                ' RandomDriveCaller: <seed_value> must either be an integer value or an MBVar' +
                '\n-------------------\n'
            )
            self.seed_value = kwargs[arg]
        except KeyError:
            pass   
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}'.format(self.idx)
        s = s + ', {}, {}'.format(self.type, self.amplitude_value)
        s = s + ', {}, {}'.format(self.mean_value, self.initial_time)
        s = s + ', {}'.format(self.final_time)
        try:
            s = s + ', steps, {}'.format(self.steps_to_hold_value)
        except AttributeError:
            pass
        try:
            s = s + ', seed, {}'.format(self.seed_value)
        except AttributeError:
            pass
        return s

class SampleAndHoldDriveCaller(DriveCaller):
    type = 'sample and hold'
    def __init__(self, **kwargs):
        try:
            arg = 'idx'
            assert isinstance(kwargs[arg], (Integral, MBVar)), (
                '\n-------------------\nERROR:' +
                ' SampleAndHoldDriveCaller: <idx> must either be an integer value or an MBVar' +
                '\n-------------------\n'
            )
            self.idx = kwargs[arg]
        except KeyError:
            pass
        try:
            arg = 'function'
            assert(isinstance(kwargs[arg], DriveCaller)), (
                '\n-------------------\nERROR:' +
                ' SampleAndHoldDriveCaller: <function> must be a DriveCaller' + 
                '\n-------------------\n'
            )
            self.function = kwargs[arg]
        except KeyError:
            errprint(
                '\n-------------------\nERROR:' +
                ' SampleAndHoldDriveCaller: <function> must be provided' + 
                '\n-------------------\n'
            )
        try:
            arg = 'trigger'
            assert(isinstance(kwargs[arg], DriveCaller)), (
                '\n-------------------\nERROR:' +
                ' SampleAndHoldDriveCaller: <trigger> must be a DriveCaller' + 
                '\n-------------------\n'
            )
            self.trigger = kwargs[arg]
        except KeyError:
            errprint(
                '\n-------------------\nERROR:' +
                ' SampleAndHoldDriveCaller: <trigger> must be provided' + 
                '\n-------------------\n'
            )
        try:
            arg = 'initial_value'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                '\n-------------------\nERROR:' +
                ' SampleAndHoldDriveCaller: <initial_value> must either be a number or an MBVar' + 
                '\n-------------------\n'
            )
            self.initial_value = kwargs[arg]
        except KeyError:
            errprint(
                '\n-------------------\nWARNING:' +
                ' SampleAndHoldDriveCaller: <initial_value> not provided, assuming 0.' + 
                '\n-------------------\n'
            )
            self.initial_value = 0.
        def __str__(self):
            s = ''
            if self.idx >= 0:
                s = s + 'drive caller: {}, '.format(self.idx)
            s = s + '{}'.format(self.type)
            if self.function.idx < 0:
                s = s + ',\n\t{}'.format(self.function)
            else:
                s = s + ',\n\treference, {}'.format(self.function.idx)
            if self.trigger.idx < 0:
                s = s + ',\n\t{}'.format(self.trigger)
            else:
                s = s + ',\n\treference, {}'.format(self.trigger.idx)
            try:
                s = s + ', initial value, {}'.format(self.initial_value)
            except AttributeError:
                pass
            return s

class StepDriveCaller(DriveCaller):
    type = 'step'
    def __init__(self, **kwargs):
        try:
            arg = 'idx'
            assert isinstance(kwargs[arg], (Integral, MBVar)), (
                '\n-------------------\nERROR:' +
                ' StepDriveCaller: <idx> must either be an integer value or an MBVar' + 
                '\n-------------------\n')
            self.idx = kwargs[arg]
        except KeyError:
            pass
        try:
            arg = 'initial_time'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                '\n-------------------\nERROR:' +
                ' StepDriveCaller: <initial_time> must either be a number or an MBVar' + 
                '\n-------------------\n')
            self.initial_time = kwargs[arg]
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' StepDriveCaller: <initial_time> not set, assuming 0.' + 
                '\n-------------------\n')
            self.initial_time = 0.
        try:
            arg = 'step_value'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                '\n-------------------\nERROR:' +
                ' StepDriveCaller: <step_value> must either be a number or an MBVar' + 
                '\n-------------------\n')
            self.step_value = kwargs[arg]
        except KeyError:
            (
                '\n-------------------\nERROR:' +
                ' StepDriveCaller: <step_value> is not set' + 
                '\n-------------------\n')
        try:
            arg = 'initial_value'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' StepDriveCaller: <initial_value> must either be a number or an MBVar' + 
                    '\n-------------------\n')
            self.initial_value = kwargs[arg]
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' StepDriveCaller: <initial_value> is not set, assuming 0.' + 
                '\n-------------------\n')
            self.initial_value = 0.
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}'.format(self.type)
        s = s + ',\n\t{}, {}'.format(self.initial_time, self.step_value)
        s = s + ',\n\t{}'.format(self.initial_value)
        return s
    
class TanhDriveCaller(DriveCaller):
    type = 'tanh'
    def __init__(self, **kwargs):
        try:
            arg = 'idx'
            assert isinstance(kwargs[arg], (Integral, MBVar)), (
                '\n-------------------\nERROR:' +
                ' TanhDriveCaller: <idx> must either be an integer value or an MBVar' + 
                '\n-------------------\n'
            )
            self.idx = kwargs[arg]
        except KeyError:
            pass
        try:
            arg = 'initial_time'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                '\n-------------------\nERROR:' +
                ' TanhDriveCaller: <initial_time> must either be a number or an MBVar' + 
                '\n-------------------\n')
            self.initial_time = kwargs[arg]
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' TanhDriveCaller: <initial_time> not set, assuming 0.' + 
                '\n-------------------\n')
            self.initial_time = 0.
        try:
            arg = 'amplitude'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                '\n-------------------\nERROR:' +
                ' TanhDriveCaller: <amplitude> must either be a number or an MBVar' + 
                '\n-------------------\n'
            )
            self.amplitude = kwargs[arg]
        except KeyError:
            errprint(
                '\n-------------------\nERROR:' +
                ' TanhDriveCaller: <amplitude> is required' + 
                '\n-------------------\n'
            )
        try:
            arg = 'slope'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                '\n-------------------\nERROR:' +
                ' TanhDriveCaller: <slope> must either be a number or an MBVar' +
                '\n-------------------\n'
            )
            self.slope = kwargs[arg]
        except KeyError:
            errprint(
                '\n-------------------\nERROR:' +
                ' TanhDriveCaller: <slope> is required' +
                '\n-------------------\n'
            )
        try:
            arg = 'initial_value'
            assert isinstance(kwargs[arg], (Number, MBVar)), (
                '\n-------------------\nERROR:' +
                ' TanhDriveCaller: <initial_value> must either be a number or an MBVar' + 
                '\n-------------------\n')
            self.initial_value = kwargs[arg]
        except KeyError:
            (
                '\n-------------------\nWARNING:' +
                ' TanhDriveCaller: <initial_value> is not set, assuming 0.' + 
                '\n-------------------\n')
            self.initial_value = 0.
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}, {}, '.format(self.type, self.initial_time)
        s = s + '{}, {}, '.format(self.amplitude, self.slope)
        s = s + '{}'.format(self.initial_value)
        return s
    
class TimeDriveCaller(DriveCaller):
    type = 'time'
    def __init__(self, **kwargs):
        try:
            arg = 'idx'
            assert isinstance(kwargs[arg], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' TimeDriveCaller: <idx> must either be an integer value or an MBVar' + 
                    '\n-------------------\n')
            self.idx = kwargs[arg]
        except KeyError:
            pass
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}'.format(self.type)
        return s
    
class TimestepDriveCaller(DriveCaller):
    type = 'timestep'
    def __init__(self, **kwargs):
        try:
            arg = 'idx'
            assert isinstance(kwargs[arg], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' TimestepDriveCaller: <idx> must either be an integer value or an MBVar' + 
                    '\n-------------------\n')
            self.idx = kwargs[arg]
        except KeyError:
            pass
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}'.format(self.type)
        return s
    
class UnitDriveCaller(DriveCaller):
    type = 'unit'
    def __init__(self, **kwargs):
        try:
            arg = 'idx'
            assert isinstance(kwargs[arg], (Integral, MBVar)), (
                    '\n-------------------\nERROR:' +
                    ' UnitDriveCaller: <idx> must either be an integer value or an MBVar' + 
                    '\n-------------------\n')
            self.idx = kwargs[arg]
        except KeyError:
            pass
    def __str__(self):
        s = ''
        if self.idx >= 0:
            s = s + 'drive caller: {}, '.format(self.idx)
        s = s + '{}'.format(self.type)
        return s
    
class TplDriveCaller(DriveCaller2):
    pass

if imported_pydantic:
    DriveDisplacement.model_rebuild()
    DriveDisplacementPin.model_rebuild()
    DriveHinge.model_rebuild()

    AngularAcceleration.model_rebuild()
    AngularVelocity.model_rebuild()
    AxialRotation.model_rebuild()
    Brake.model_rebuild()
    ImposedDisplacement.model_rebuild()
    ImposedDisplacement.model_rebuild()


class ConstitutiveLaw(MBEntity):
    """
    Abstract class for C++ type `ConstitutiveLaw`. Every time a “deformable”
    entity requires a constitutive law, a template constitutive law is read. This has been implemented by
    means of C++ templates in order to allow the definition of a general constitutive law when possible.

    Constitutive laws are also used in non-structural components, to allow some degree of generality in
    defining input/output relationships. Some constitutive laws are meaningful only when related to some
    precise dimensionality. In some special cases, general purpose elements use 1D constitutive laws
    to express an arbitrary dependence of some value on a scalar state of the system.

    The meaning of the input and output parameters of a constitutive law is dictated by the entity that
    uses it. In general, the user should refer to the element the constitutive law is being instantiated for in
    order to understand what the input and the output parameters are supposed to be.
    """

    # class Config:
    #     arbitrary_types_allowed = True

    class LawType(Enum):
        SCALAR_ISOTROPIC_LAW = "scalar isotropic law"
        D3_ISOTROPIC_LAW = "3D isotropic law"
        D6_ISOTROPIC_LAW = "6D isotropic law"

    idx: Optional[Union[MBVar, int]] = None
    """Index of this constitutive law to reuse with references"""

    law_type: LawType

    @abstractmethod
    def const_law_name(self) -> str:
        """Name of the specific constitutive law"""
        pass

    @property
    def dim(self) -> int:
        """Determine the dimensionality based on the constitutive law name"""
        if self.law_type == ConstitutiveLaw.LawType.SCALAR_ISOTROPIC_LAW:
            return 1
        elif self.law_type == ConstitutiveLaw.LawType.D3_ISOTROPIC_LAW:
            return 3
        elif self.law_type == ConstitutiveLaw.LawType.D6_ISOTROPIC_LAW:
            return 6
        else: 
            raise ValueError(f"Unknown constitutive law name: {self.law_type}") 
        
    def const_law_header(self) -> str:
        """Common syntax for start of any constitutive law"""
        if self.idx is not None and self.idx >= 0:
            return f'constitutive law: {self.idx}, name, "{self.law_type.value}",' \
                   f'\n\t{self.dim}, {self.const_law_name()}'
        else:
            return self.const_law_name()
    
class LinearElastic(ConstitutiveLaw):
    """
    Linear elastic constitutive law
    """
        
    def const_law_name(self) -> str:
        if self.dim == 1:
            return 'linear elastic'
        else:
            return 'linear elastic isotropic'
    
    stiffness: Union[MBVar, float]
    """The isotropic stiffness coefficient"""
    
    def __str__(self):
        return f'{self.const_law_header()}, {self.stiffness}'

class LinearElasticGeneric(ConstitutiveLaw):
    """
    Linear elastic generic constitutive law
    """

    stiffness: Union[float, MBVar, List[List[Union[float, MBVar]]]]
    
    def const_law_name(self) -> str:
        return 'linear elastic generic'

    def __str__(self):
        if isinstance(self.stiffness, (float, MBVar)):
            return f'{self.const_law_header()}, {self.stiffness}'
        elif isinstance(self.stiffness, list):
            N = len(self.stiffness)
            if N == 1:
                return f'{self.const_law_header()}, {self.stiffness[0][0]}'
            elif N == 3 or N == 6:
                matrix_str = ''
                for i in range(N):
                    row_str = ', '.join(str(self.stiffness[i][j]) for j in range(N))
                    matrix_str += f',\n\t{row_str}'
                return f'{self.const_law_header()}{matrix_str}'
            else:
                raise ValueError("Unsupported size of stiffness matrix")
        else:
            raise TypeError("Invalid type for stiffness matrix")        

class LinearElasticGenericAxialTorsionCoupling(ConstitutiveLaw):
    """
    Linear elastic generic axial torsion coupling constitutive law
    """

    stiffness: Union[List[List[Union[float, MBVar]]]]
    coupling_coef: Union[float, MBVar]

    def const_law_name(self) -> str:
        return 'linear elastic generic axial torsion coupling'

    def __str__(self):
        base_str = f'{self.const_law_header()}'
        matrix_str = ''
        N = 6 
        for i in range(N):
            row_str = ', '.join(str(self.stiffness[i][j]) for j in range(N))
            matrix_str += f',\n\t{row_str}'

        base_str = f'{base_str}{matrix_str},\n\t{self.coupling_coef}'
        return base_str
    
class CubicElasticGeneric(ConstitutiveLaw):
    """
    Cubic elastic generic constitutive law
    """

    ### TODO: Ensure this is the correct data type
    stiffness_1: Union[float, MBVar, List[Union[float, MBVar]]]
    stiffness_2: Union[float, MBVar, List[Union[float, MBVar]]]
    stiffness_3: Union[float, MBVar, List[Union[float, MBVar]]]
    
    def const_law_name(self) -> str:
        return 'cubic elastic generic'

    ### TODO: Ensure this is the correct string representation
    def __str__(self):
        base_str = f'{self.const_law_header()}'
        if isinstance(self.stiffness_1, (float, MBVar)):
            base_str += f', {self.stiffness_1}, {self.stiffness_2}, {self.stiffness_3}'
        elif isinstance(self.stiffness_1, list):
            N = len(self.stiffness_1)
            if N == 3:
                stiffness_1_str = ', '.join(str(self.stiffness_1[i]) for i in range(N))
                stiffness_2_str = ', '.join(str(self.stiffness_2[i]) for i in range(N))
                stiffness_3_str = ', '.join(str(self.stiffness_3[i]) for i in range(N))
                base_str += f',\n\t{stiffness_1_str},\n\t{stiffness_2_str},\n\t{stiffness_3_str}'
            else:
                raise ValueError("Unsupported size of stiffness vector")
        else:
            raise TypeError("Invalid type for stiffness values")
        return base_str


class InverseSquareElastic(ConstitutiveLaw):
    """
    Inverse square elastic constitutive law
    """
    
    stiffness: Union[MBVar, float]
    ref_length: Union[MBVar, float]
    
    def const_law_name(self) -> str:
        return 'inverse square elastic'
    
    def __str__(self):
        return f'{self.const_law_header()}, {self.stiffness}, {self.ref_length}'
    
class LogElastic(ConstitutiveLaw):
    """
    Logarithmic elastic constitutive law
    """

    stiffness: Union[float, MBVar]

    def const_law_name(self) -> str:
        return 'log elastic'

    def __str__(self):
        return f'{self.const_law_header()}, {self.stiffness}'

class LinearElasticBistop(ConstitutiveLaw):
    """
    Linear elastic bistop constitutive law
    """

    class Config:
        arbitrary_types_allowed = True

    stiffness: Union[float, MBVar]
    initial_status: Optional[Union[bool, str]]
    activating_condition: Union[DriveCaller, DriveCaller2] 
    deactivating_condition: Union[DriveCaller, DriveCaller2]

    def const_law_name(self) -> str:
        return 'linear elastic bistop'

    # TODO: Ensure the string representation is correct
    def __str__(self):
        base_str = f'{self.const_law_header()}, {self.stiffness}'
        
        if self.initial_status is not None:
            base_str += f',\n\tinitial status, {self.initial_status},'

        base_str += '\n\t# activation condition drive'
        if self.activation_condition.idx is None:
            base_str += f'\n\t{self.activation_condition},'
        else:
            base_str += f'\n\treference, {self.activation_condition.idx},'
        base_str += '\n\t# activation condition drive'
        if self.deactivating_condition.idx is None:
            base_str += f'\n\t{self.deactivating_condition},'
        else:
            base_str += f'\n\treference, {self.deactivating_condition.idx}'

        return base_str

class DoubleLinearElastic(ConstitutiveLaw):
    """
    Double linear elastic constitutive law
    """

    stiffness_1: Union[MBVar, float]
    upper_strain: Union[MBVar, float]
    lower_strain: Union[MBVar, float]
    stiffness_2: Union[MBVar, float]
    
    def const_law_name(self) -> str:
        return 'double linear elastic'
    
    def __str__(self):
        return f'{self.const_law_header()}, {self.stiffness_1}, {self.upper_strain}, {self.lower_strain}, {self.stiffness_2}'

class IsotropicHardeningElastic(ConstitutiveLaw):
    """
    Isotropic hardening elastic constitutive law
    """

    stiffness: Union[MBVar, float]
    reference_strain: Union[MBVar, float]
    linear_stiffness: Optional[Union[MBVar, float]]
    
    def const_law_name(self) -> str:
        return 'isotropic hardening elastic'
    
    def __str__(self):
        if self.linear_stiffness is not None:
            return f'{self.const_law_header()}, {self.stiffness}, {self.reference_strain}, linear stiffness, {self.linear_stiffness}'
        else:
            return f'{self.const_law_header()}, {self.stiffness}, {self.reference_strain}'
        
class LinearViscous(ConstitutiveLaw):
    """
    Linear viscous constitutive law
    """

    viscosity: Union[MBVar, float]    
    
    def const_law_name(self) -> str:
        if self.dim == 1:
            return 'linear viscous'
        else:
            return 'linear viscous isotropic'

    def __str__(self):
        return f'{self.const_law_header()}, {self.viscosity}'

class LinearViscousGeneric(ConstitutiveLaw):
    """
    Linear viscous generic constitutive law
    """

    viscosity: Union[float, MBVar, List[List[Union[float, MBVar]]]]

    def const_law_name(self) -> str:
        return 'linear viscous generic'

    def __str__(self):
        if isinstance(self.viscosity, (float, MBVar)):
            return f'{self.const_law_header()}, {self.viscosity}'
        elif isinstance(self.viscosity, list):
            N = len(self.viscosity)
            if N == 1:
                return f'{self.const_law_header()}, {self.viscosity[0][0]}'
            elif N == 3 or N == 6:
                matrix_str = ''
                for i in range(N):
                    row_str = ', '.join(str(self.viscosity[i][j]) for j in range(N))
                    matrix_str += f',\n\t{row_str}'
                return f'{self.const_law_header()}{matrix_str}'
            else:
                raise ValueError("Unsupported size of viscosity matrix")
        else:
            raise TypeError("Invalid type for viscosity matrix")
 
class LinearViscoelastic(ConstitutiveLaw):
    """
    Linear viscoelastic constitutive law
    """

    stiffness: Union[MBVar, float]

    viscosity: Union[MBVar, float]
    """The viscosity coefficient"""

    factor: Optional[Union[MBVar, float]]
    """Factor for proportional viscosity"""
    
    def const_law_name(self) -> str:
        if self.dim == 1:
            return 'linear viscoelastic'
        else:
            return 'linear viscoelastic isotropic'

    def __str__(self):
        if self.viscosity is not None:
            return f'{self.const_law_header()}, {self.stiffness}, {self.viscosity}'
        elif self.factor is not None:
            return f'{self.const_law_header()}, {self.stiffness}, proportional, {self.factor}'
        else:
            raise ValueError("Either viscosity or factor must be provided for Linear viscoelastic law")
        
class LinearViscoelasticGeneric(ConstitutiveLaw):
    """
    Linear viscoelastic generic constitutive law
    """

    stiffness: List[List[Union[float, MBVar]]]
    viscosity: Optional[List[List[Union[float, MBVar]]]] = None
    factor: Optional[Union[float, MBVar]] = None

    @model_validator(mode='before')
    def check_viscosity_factor(cls, values: 'FieldValidationInfo') -> Any:
        stiffness = values.get('stiffness')
        viscosity = values.get('viscosity')
        factor = values.get('factor')
        # Ensure either viscosity or factor is provided, but not both
        if viscosity is not None and factor is not None:
            raise ValueError("Either viscosity or factor must be provided, not both.")
        if viscosity is None and factor is None:
            raise ValueError("One of viscosity or factor must be provided.")

        def validate_matrix(matrix: List[List[Union[float, MBVar]]], name: str) -> None:
            """Validate the matrix to ensure it's a square matrix of size 3x3 or 6x6."""
            if matrix:
                N = len(matrix)
                if N not in {3, 6}:
                    raise ValueError(f"Unsupported size of {name} matrix. Expected 3x3 or 6x6, got {N}x{N}.")
                for row in matrix:
                    if len(row) != N:
                        raise ValueError(f"{name.capitalize()} matrix must be square. Expected {N}x{N}, but found a row with length {len(row)}.")
        # Validate stiffness matrix
        if stiffness:
            validate_matrix(stiffness, 'stiffness')
        # Validate viscosity matrix
        if viscosity:
            validate_matrix(viscosity, 'viscosity')
        return values
    
    def const_law_name(self) -> str:
        return 'linear viscoelastic generic'
    
    def __str__(self):
        base_str = f'{self.const_law_header()}'
        if isinstance(self.stiffness, (float, MBVar)):
            base_str += f', {self.stiffness}'
        elif isinstance(self.stiffness, list):
            N = len(self.stiffness)
            if N == 1:
                base_str += f', {self.stiffness[0][0]}'
            elif N == 3 or N == 6:
                matrix_str = ''
                for i in range(N):
                    row_str = ', '.join(str(self.stiffness[i][j]) for j in range(N))
                    matrix_str += f',\n\t{row_str}'
                base_str += f'{matrix_str}'
            else:
                raise ValueError("Unsupported size of stiffness matrix")
        else:
            raise TypeError("Invalid type for stiffness matrix")
        if self.viscosity is not None:
            if isinstance(self.viscosity, (float, MBVar)):
                base_str += f', {self.viscosity}'
            elif isinstance(self.viscosity, list):
                N = len(self.viscosity)
                if N == 1:
                    base_str += f', {self.viscosity[0][0]}'
                elif N == 3 or N == 6:
                    matrix_str = ''
                    for i in range(N):
                        row_str = ', '.join(str(self.viscosity[i][j]) for j in range(N))
                        matrix_str += f',\n\t{row_str}'
                    base_str += f'{matrix_str}'
                else:
                    raise ValueError("Unsupported size of viscosity matrix")
            else:
                raise TypeError("Invalid type for viscosity matrix")
        elif self.factor is not None:
            base_str += f', proportional, {self.factor}'
        return base_str
   
class LinearTimeVariantViscoelasticGeneric(ConstitutiveLaw):
    """
    Linear time variant viscoelastic generic constitutive law
    """

    class Config:
        arbitrary_types_allowed = True

    stiffness: Union[float, MBVar, List[List[Union[float, MBVar]]]]
    stiffness_scale: Union[DriveCaller, DriveCaller2]
    viscosity: Optional[Union[float, MBVar, List[List[Union[float, MBVar]]]]] = None
    factor: Optional[Union[float, MBVar]] = None
    viscosity_scale: Union[DriveCaller, DriveCaller2]

    def const_law_name(self) -> str:
        return 'linear time variant viscoelastic generic'

    def __str__(self):
        base_str = f'{self.const_law_header()}'
        
        # String representation for stiffness
        if isinstance(self.stiffness, (float, MBVar)):
            base_str += f', {self.stiffness}'
        elif isinstance(self.stiffness, list):
            N = len(self.stiffness)
            if N == 1:
                base_str += f', {self.stiffness[0][0]}'
            elif N == 3 or N == 6:
                matrix_str = ''
                for i in range(N):
                    row_str = ', '.join(str(self.stiffness[i][j]) for j in range(N))
                    matrix_str += f',\n\t{row_str}'
                base_str += f'{matrix_str}'
            else:
                raise ValueError("Unsupported size of stiffness matrix")
        else:
            raise TypeError("Invalid type for stiffness matrix")

        # String representation for stiffness scale
        if self.stiffness_scale.idx is None:
            base_str += f',\n\t{self.stiffness_scale},'
        else:
            base_str += f',\n\treference, {self.stiffness_scale.idx},'
        
        # String representation for viscosity
        if self.viscosity is not None:
            if isinstance(self.viscosity, (float, MBVar)):
                base_str += f', {self.viscosity}'
            elif isinstance(self.viscosity, list):
                N = len(self.viscosity)
                if N == 1:
                    base_str += f', {self.viscosity[0][0]}'
                elif N == 3 or N == 6:
                    matrix_str = ''
                    for i in range(N):
                        row_str = ', '.join(str(self.viscosity[i][j]) for j in range(N))
                        matrix_str += f',\n\t{row_str}'
                    base_str += f',\n{matrix_str}'
                else:
                    raise ValueError("Unsupported size of viscosity matrix")
            else:
                raise TypeError("Invalid type for viscosity matrix")
        elif self.factor is not None:
            base_str += f', proportional, {self.factor}'
        else:
            raise ValueError("Either viscosity or factor must be provided")

        # String representation for viscosity scale
        if self.viscosity_scale.idx is None:
            base_str += f',\n\t{self.viscosity_scale}'
        else:
            base_str += f',\n\treference, {self.viscosity_scale.idx}'

        return base_str

class LinearViscoelasticGenericAxialTorsionCoupling(ConstitutiveLaw):
    """
    Linear viscoelastic generic axial torsion coupling constitutive law
    """

    stiffness: List[List[Union[float, MBVar]]]
    viscosity: Optional[List[List[Union[float, MBVar]]]] = None
    factor: Optional[Union[float, MBVar]] = None
    coupling_coef: float

    def const_law_name(self) -> str:
        return 'linear viscoelastic generic axial torsion coupling'

    def __str__(self):
        base_str = f'{self.const_law_header()}'
        
        # String representation for stiffness
        if isinstance(self.stiffness, list):
            N = len(self.stiffness)
            if N != 6:
                raise ValueError("Stiffness matrix must be 6x1")
            matrix_str = ', '.join(str(self.stiffness[i][0]) for i in range(N))
            base_str += f',\n\t{matrix_str}'
        else:
            raise TypeError("Invalid type for stiffness matrix")

        # String representation for viscosity or factor
        if self.viscosity is not None:
            if isinstance(self.viscosity, list):
                N = len(self.viscosity)
                if N != 6:
                    raise ValueError("Viscosity matrix must be 6x1")
                matrix_str = ', '.join(str(self.viscosity[i][0]) for i in range(N))
                base_str += f',\n\t{matrix_str}'
            else:
                raise TypeError("Invalid type for viscosity matrix")
        elif self.factor is not None:
            base_str += f', proportional, {self.factor}'
        else:
            raise ValueError("Either viscosity or factor must be provided")

        # Adding the coupling coefficient
        base_str += f',\n\t{self.coupling_coef}'

        return base_str

class CubicViscoelasticGeneric(ConstitutiveLaw):
    """
    Cubic viscoelastic generic constitutive law
    """

    stiffness_1: Union[float, MBVar, List[Union[float, MBVar]]]
    stiffness_2: Union[float, MBVar, List[Union[float, MBVar]]]
    stiffness_3: Union[float, MBVar, List[Union[float, MBVar]]]
    viscosity: Union[float, MBVar, List[Union[float, MBVar]]]

    def const_law_name(self) -> str:
        return 'cubic viscoelastic generic'

    def __str__(self):
        base_str = f'{self.const_law_header()}'
        if isinstance(self.stiffness_1, (float, MBVar)):
            base_str += f', {self.stiffness_1}, {self.stiffness_2}, {self.stiffness_3}, {self.viscosity}'
        elif isinstance(self.stiffness_1, list):
            N = len(self.stiffness_1)
            if N == 3:
                stiffness_1_str = ', '.join(str(self.stiffness_1[i]) for i in range(N))
                stiffness_2_str = ', '.join(str(self.stiffness_2[i]) for i in range(N))
                stiffness_3_str = ', '.join(str(self.stiffness_3[i]) for i in range(N))
                viscosity_str = ', '.join(str(self.viscosity[i]) for i in range(N))
                base_str += f',\n\t{stiffness_1_str},\n\t{stiffness_2_str},\n\t{stiffness_3_str},\n\t{viscosity_str}'
            else:
                raise ValueError("Unsupported size of stiffness and viscosity vectors")
        else:
            raise TypeError("Invalid type for stiffness and viscosity values")
        return base_str
    
class DoubleLinearViscoelastic(ConstitutiveLaw):
    """
    Double linear viscoelastic constitutive law
    """

    stiffness_1: Union[MBVar, float]
    upper_strain: Union[MBVar, float]
    lower_strain: Union[MBVar, float]
    stiffness_2: Union[MBVar, float]
    viscosity: Union[MBVar, float]
    viscosity_2: Optional[Union[MBVar, float]] = None

    def const_law_name(self) -> str:
        return 'double linear viscoelastic'

    def __str__(self):
        base_str = f'{self.const_law_header()}, {self.stiffness_1}, {self.upper_strain}, {self.lower_strain}, {self.stiffness_2}, {self.viscosity}'
        if self.viscosity_2 is not None:
            return f'{base_str}, second damping, {self.viscosity_2}'
        else:
            return base_str
        
class TurbulentViscoelastic(ConstitutiveLaw):
    """
    Turbulent viscoelastic constitutive law
    """

    stiffness: Union[MBVar, float]
    parabolic_viscosity: Union[MBVar, float]
    threshold: Optional[Union[MBVar, float]] = None
    linear_viscosity: Optional[Union[MBVar, float]] = None

    def const_law_name(self) -> str:
        return 'turbulent viscoelastic'

    def __str__(self):
        base_str = f'{self.const_law_header()}, {self.stiffness}, {self.parabolic_viscosity}'
        if self.threshold is not None:
            base_str += f', {self.threshold}'
            if self.linear_viscosity is not None:
                base_str += f', {self.linear_viscosity}'
        return base_str

class LinearViscoelasticBistop(ConstitutiveLaw):
    """
    Linear viscoelastic bistop constitutive law
    """

    class Config:
        arbitrary_types_allowed = True

    stiffness: Union[float, MBVar]
    viscosity: Union[float, MBVar]
    initial_status: Optional[Union[bool, str]] = None
    activating_condition: Union[DriveCaller, DriveCaller2]
    deactivating_condition: Union[DriveCaller, DriveCaller2]

    def const_law_name(self) -> str:
        return 'linear viscoelastic bistop'

    def __str__(self):
        base_str = f'{self.const_law_header()}, {self.stiffness}, {self.viscosity}'
        if self.initial_status is not None:
            base_str += f',\n\tinitial status, {self.initial_status},'
        base_str += '\n\t# activation condition drive'
        if self.activating_condition.idx is None:
            base_str += f'\n\t{self.activating_condition},'
        else:
            base_str += f'\n\treference, {self.activating_condition.idx},'
        base_str += '\n\t# deactivation condition drive'
        if self.deactivating_condition.idx is None:
            base_str += f'\n\t{self.deactivating_condition}'
        else:
            base_str += f'\n\treference, {self.deactivating_condition.idx}'
        return base_str

class SymbolicElastic(ConstitutiveLaw):
    """
    Symbolic elastic constitutive law
    """

    epsilon: Union[str, List[str]]
    expression: Union[str, List[str]]

    def const_law_name(self) -> str:
        return 'symbolic elastic'

    def __str__(self):
        base_str = f'{self.const_law_header()}'

        if isinstance(self.epsilon, str):
            epsilon_list = [self.epsilon]
        else:
            epsilon_list = self.epsilons
        if isinstance(self.expressions, str):
            expression_list = [self.expression]
        else:
            expression_list = self.expression
        if len(epsilon_list) != len(expression_list):
            raise ValueError("The number of epsilons must match the number of expressions")
        
        epsilon_str = ', '.join(f'"{epsilon}"' for epsilon in epsilon_list)
        base_str += f',\n\tepsilon, {epsilon_str}'
        expression_str = ', '.join(f'"{expression}"' for expression in expression_list)
        base_str += f',\n\texpression, {expression_str}'
        return base_str

class SymbolicViscous(ConstitutiveLaw):
    """
    Symbolic viscous constitutive law
    """

    epsilon_prime: Union[str, List[str]]
    expression: Union[str, List[str]]

    def const_law_name(self) -> str:
        return 'symbolic viscous'

    def __str__(self):
        base_str = f'{self.const_law_header()}'

        if isinstance(self.epsilon_prime, str):
            epsilon_prime_list = [self.epsilon_prime]
        else:
            epsilon_prime_list = self.epsilon_prime
        if isinstance(self.expression, str):
            expression_list = [self.expression]
        else:
            expression_list = self.expression
        if len(epsilon_prime_list) != len(expression_list):
            raise ValueError("The number of epsilon_primes must match the number of expressions")

        epsilon_prime_str = ', '.join(f'"{epsilon_prime}"' for epsilon_prime in epsilon_prime_list)
        base_str += f',\n\tepsilon prime, {epsilon_prime_str}'
        expression_str = ', '.join(f'"{expression}"' for expression in expression_list)
        base_str += f',\n\texpression, {expression_str}'
        return base_str
    
class SymbolicViscoelastic(ConstitutiveLaw):
    """
    Symbolic viscoelastic constitutive law
    """

    epsilon: Union[str, List[str]]
    epsilon_prime: Union[str, List[str]]
    expression: Union[str, List[str]]

    def const_law_name(self) -> str:
        return 'symbolic viscoelastic'

    def __str__(self):
        base_str = f'{self.const_law_header()}'

        if isinstance(self.epsilon, str):
            epsilon_list = [self.epsilon]
        else:
            epsilon_list = self.epsilon
        if isinstance(self.epsilon_prime, str):
            epsilon_prime_list = [self.epsilon_prime]
        else:
            epsilon_prime_list = self.epsilon_prime
        if isinstance(self.expression, str):
            expression_list = [self.expression]
        else:
            expression_list = self.expression
        if len(epsilon_list) != len(epsilon_prime_list) or len(epsilon_list) != len(expression_list):
            raise ValueError("The number of epsilons, epsilon_primes, and expressions must match")

        epsilon_str = ', '.join(f'"{epsilon}"' for epsilon in epsilon_list)
        epsilon_prime_str = ', '.join(f'"{epsilon_prime}"' for epsilon_prime in epsilon_prime_list)
        expression_str = ', '.join(f'"{expression}"' for expression in expression_list)
        base_str += f',\n\tepsilon, {epsilon_str}'
        base_str += f',\n\tepsilon prime, {epsilon_prime_str}'
        base_str += f',\n\texpression, {expression_str}'
        return base_str
    
class SymbolicViscoelastic(ConstitutiveLaw):
    """
    Symbolic viscoelastic constitutive law
    """

    epsilon: Union[str, List[str]]
    epsilon_prime: Union[str, List[str]]
    expression: Union[str, List[str]]

    def const_law_name(self) -> str:
        return 'symbolic viscoelastic'

    def __str__(self):
        base_str = f'{self.const_law_header()}'

        if isinstance(self.epsilon, str):
            epsilon_list = [self.epsilon]
        else:
            epsilon_list = self.epsilon
        if isinstance(self.epsilon_prime, str):
            epsilon_prime_list = [self.epsilon_prime]
        else:
            epsilon_prime_list = self.epsilon_prime
        if isinstance(self.expression, str):
            expression_list = [self.expression]
        else:
            expression_list = self.expression
        if len(epsilon_list) != len(epsilon_prime_list) or len(epsilon_list) != len(expression_list):
            raise ValueError("The number of epsilons, epsilon_primes, and expressions must match")

        epsilon_str = ', '.join(f'"{epsilon}"' for epsilon in epsilon_list)
        epsilon_prime_str = ', '.join(f'"{epsilon_prime}"' for epsilon_prime in epsilon_prime_list)
        expression_str = ', '.join(f'"{expression}"' for expression in expression_list)
        base_str += f',\n\tepsilon, {epsilon_str}'
        base_str += f',\n\tepsilon prime, {epsilon_prime_str}'
        base_str += f',\n\texpression, {expression_str}'
        return base_str
    
class AnnElastic(ConstitutiveLaw):
    """
    Ann elastic constitutive law
    """

    file_name: str

    def const_law_name(self) -> str:
        return 'ann elastic'

    def __str__(self):
        base_str = f'{self.const_law_header()}'
        base_str += f',\n\t"{self.file_name}"'
        return base_str

class AnnViscoelastic(ConstitutiveLaw):
    """
    Ann viscoelastic constitutive law
    """

    file_name: str

    def const_law_name(self) -> str:
        return 'ann viscoelastic'

    def __str__(self):
        base_str = f'{self.const_law_header()}'
        base_str += f',\n\t"{self.file_name}"'
        return base_str

class ArrayConstitutiveLaw(ConstitutiveLaw):
    """
    Array constitutive law wrapper linearly combines the output of multiple constitutive laws.
    """

    number: int
    wrapped_const_laws: List[ConstitutiveLaw]

    def const_law_name(self) -> str:
        return 'array'

    def __str__(self):
        if self.number == 1:
            return str(self.wrapped_const_laws[0])

        base_str = f'{self.const_law_header()}, {self.number}'
        for law in self.wrapped_const_laws:
            base_str += f',\n\t{str(law)}'
        return base_str

class BistopConstitutiveLaw(ConstitutiveLaw):
    """
    Bistop wrapper applies the logic of the bistop to a generic underlying constitutive law.
    """

    class Config:
        arbitrary_types_allowed = True

    initial_status: Optional[Union[bool, str]]
    activating_condition: Union[DriveCaller, DriveCaller2]
    deactivating_condition: Union[DriveCaller, DriveCaller2]
    wrapped_const_law: ConstitutiveLaw

    def const_law_name(self) -> str:
        return 'bistop'

    def __str__(self):
        base_str = f'{self.const_law_header()}'
        if self.initial_status is not None:
            base_str += f',\n\tinitial status, {self.initial_status},'

        base_str += '\n\t# activation condition drive'
        if self.activating_condition.idx is None:
            base_str += f'\n\t{self.activating_condition},'
        else:
            base_str += f'\n\treference, {self.activating_condition.idx},'
        base_str += '\n\t# deactivation condition drive'
        if self.deactivating_condition.idx is None:
            base_str += f'\n\t{self.deactivating_condition},'
        else:
            base_str += f'\n\treference, {self.deactivating_condition.idx},'

        base_str += f'\n\t{str(self.wrapped_const_law)}'
        return base_str

class InvariantAngularWrapper(ConstitutiveLaw):
    """
    Invariant angular wrapper for 3D constitutive laws used within the “attached” variant of the deformable hinge joint.
    """

    xi: Union[float, int, MBVar]
    wrapped_const_law: ConstitutiveLaw

    def const_law_name(self) -> str:
        return 'invariant angular'

    def __str__(self):
        base_str = f'{self.const_law_header()}'
        base_str += f',\n\t{self.xi}'
        base_str += f',\n\t{str(self.wrapped_const_law)}'
        return base_str
    
class NamedConstitutiveLaw(MBEntity):
    """
    Adapter for using a constitutive law that is not yet implemented in the preprocessor
    as a regular `ConstitutiveLaw` subclass with argument checking.

    This should only be used temporarily, and may be removed in the future without prior notice.
    """
    
    content: str
    """Text that will be output to MBDyn for this law"""

    def __init__(self, law: Union[str, list]):
        warnings.warn(
            "Using a string for constitutive laws is not recommended " + \
            "and may be removed in the future. " + \
            "Consider using ConstitutiveLaw instances for better support.",
            UserWarning
        )
        if isinstance(law, list):
            law = ', '.join(str(l) for l in law)
        else:
            law = str(law)
        super().__init__(content=law)

    def __str__(self):
        return self.content

if imported_pydantic:
    DeformableAxial.model_rebuild()
    DeformableHinge2.model_rebuild()
    Rod2.model_rebuild()
    RodWithOffset.model_rebuild()
    RodBezier.model_rebuild()
    ViscousBody.model_rebuild()

class FileDriver(MBEntity):
    """
    Abstract class for file drivers. The file drivers are defined by the statement:
    file : <file_arglist> ;
    A comprehensive family of file drivers is available.
    """
    
    idx: Union[MBVar, int]
    """Index of this file driver"""

    @abstractmethod
    def driver_type(self) -> str:
        """Every file driver must have a type"""
        pass

    def file_header(self) -> str:
        """Common syntax for start of any file driver"""
        return f'file: {self.idx}, {self.driver_type()}'
    
class FixedStep(FileDriver):
    """
    Fixed Step file driver
    """

    # class Config:
    #     arbitrary_types_allowed = True
    
    class InterpolationType(Enum):
        LINEAR = "linear"
        CONST = "const"

    class BailoutType(Enum):
        NONE = "none"
        UPPER = "upper"
        LOWER = "lower"
        ANY = "any"

    class PadZeroesType(Enum):
        YES = 'yes'
        NO = 'no'
    
    steps_number: Union[int, MBVar, str]  # 'count' or specific number of steps
    columns_number: Union[int, MBVar]
    initial_time: Union[float, MBVar, str]  # 'from file' or specific initial time
    time_step: Union[float, MBVar, str]  # 'from file' or specific time step
    interpolation: Optional[InterpolationType]
    pad_zeroes: Optional[PadZeroesType]
    bailout: Optional[BailoutType]
    file_name: str

    def driver_type(self) -> str:
        return "fixed step"
    
    def __str__(self):
        base_str = f'{self.file_header()},\n\t'
        base_str += f'{self.steps_number},\n\t'
        base_str += f'{self.columns_number},\n\t'
        base_str += f'initial time, {self.initial_time},\n\t'
        base_str += f'time step, {self.time_step},\n\t'
        if self.interpolation:
            base_str += f'interpolation, {self.interpolation.value},\n\t'
        if self.pad_zeroes == FixedStep.PadZeroesType.NO and self.bailout:
            raise ValueError("Cannot set both 'pad zeroes' to 'no' and 'bailout' at the same time")
        if self.pad_zeroes:
            base_str += f'pad zeroes, {self.pad_zeroes},\n\t'
        elif self.bailout:
            base_str += f'bailout, {self.bailout},\n\t'
        base_str += f'"{self.file_name}"'
        return base_str
    
class VariableStep(FileDriver):
    """
    Variable Step file driver
    """
    
    channels_number: Union[int, MBVar]
    interpolation: Optional[FixedStep.InterpolationType]
    pad_zeroes: Optional[FixedStep.PadZeroesType]
    bailout: Optional[FixedStep.BailoutType]
    file_name: str

    def driver_type(self) -> str:
        return "variable step"
    
    def __str__(self):
        base_str = f'{self.file_header()},\n\t'
        base_str += f'{self.channels_number},\n\t'
        if self.interpolation:
            base_str += f'interpolation, {self.interpolation.value},\n\t'
        if self.pad_zeroes == FixedStep.PadZeroesType.NO and self.bailout:
            raise ValueError("Cannot set both 'pad zeroes' to 'no' and 'bailout' at the same time")
        if self.pad_zeroes:
            base_str += f'pad zeroes, {self.pad_zeroes},\n\t'
        elif self.bailout:
            base_str += f'bailout, {self.bailout},\n\t'
        base_str += f'"{self.file_name}"'
        return base_str

# class Data:
#     problem_type = ('INITIAL VALUE', 'INVERSE DYNAMICS')
#     def __init__(self, **kwargs):
#         for key, value in kwargs.items():
#             if key == 'problem type':
#                 if value in self.problem_type:
#                     self.type = value
#                 else:
#                     raise ValueError('Unrecognised problem type')            

# class InitialValueStrategy:
#     strategy_type = ('NO CHANGE', 'FACTOR', 'CHANGE')
#     def __init__(self, stype, **kwargs):
#         if stype in self.strategy_type:
#             self.type = value
#         else:
#             raise ValueError('Unrecognised strategy')
       
#         if self.type == 'FACTOR':
#             for key, value in kwargs.items():
#                 if key == 'reduction_factor':
#                     self.reduction_factor = value
#                 if key == 'steps_before_reduction':
#                     self.steps_before_reduction = value
#                 if key == 'raise_factor':
#                     self.raise_factor = value
#                 if key == 'steps_before_raise':
#                     self.steps_before_raise = value
#                 if key == 'minimum_iterations':
#                     self.minimum_iterations = value
#                 if key == 'maximum_iterations':
#                     self.maximum_iterations = value
#         if self.self_type == 'CHANGE':
#             self.time_step_pattern = DriveCaller('const', 1e-3);

# class InitialValue:
#     def __init__(self):
#         self.initial_time = 0.
#         self.final_time = 10.
#         self.strategy = InitialValueStrategy()
#         self.min_time_step = 1e-6
#         self.max_time_step = 1.
#         self.time_step = 1e-3

class Data(MBEntity):
    problem: Union[Literal["initial value"], Literal["inverse dynamics"]] = "initial value"

    def __str__(self):
        s = 'begin: data;\n'
        s += f'\tproblem: {self.problem};\n'
        s += 'end: data;'
        return s
    

# Initial Value 
# TODO: Remove these codes as they are temporarily copied here
class Strategy(MBEntity):
    """
    Abstract base class for all Strategies
    """

    @abstractmethod
    def strategy_type(self) -> str:
        """Every strategy class must define this to return its MBDyn syntax name"""
        raise NotImplementedError("called strategy_type of abstract Element")

    def strategy_header(self) -> str:
        """common syntax for start of any strategy"""
        return f'stratefy: {self.strategy_type()}'

class StrategyFactor(Strategy):
    reduction_factor: Union[float, MBVar]
    steps_before_reduction: Union[int, MBVar]
    raise_factor: Union[float, MBVar]
    steps_before_raise: Union[int, MBVar]
    min_iterations: Union[int, MBVar]
    max_iterations: Optional[Union[int, MBVar]] = None

    def __str__(self):
        s = f'{self.strategy_header()}, {self.steps_before_reduction}'
        s += f', {self.raise_factor}, {self.steps_before_raise}, {self.min_iterations}'
        if self.max_iterations is not None:
            s += f', {self.max_iterations}'
        return s

class StrategyChange(Strategy):
    # TODO: Remove this relaxed config when all DriveCallers are refactored
    class Config:
        arbitrary_types_allowed = True

    time_step_pattern: Union[DriveCaller, DriveCaller2]

    def __str__(self):
        s = f'{self.strategy_header()}, {self.time_step_pattern}'
        return s

class StrategyNoChange(Strategy):
    def __str__(self):
        s = f'{self.strategy_header()}'
        return s
    
class Tolerance(MBEntity):
    residual_tolerance: Union[Literal['null'], float, MBVar]
    residual_test: Optional[Literal['none', 'norm', 'minmax']] = None
    scaling: Optional[str] = None
    solution_tolerance: Optional[Union[Literal['null'], float, MBVar]] = None
    solution_test: Optional[Literal['none', 'norm', 'minmax']] = None

    @field_validator('scaling')
    def validate_scaling(cls, v, info):
        residual_test = info.data.get('residual_test')
        if residual_test is None and v is not None:
            raise ValueError("scaling should be None if residual_test is not provided")
        if v is not None and v.lower() != 'scale':
            raise ValueError("scaling must be a string literal: 'scale'")
        return v.lower() if v is not None else v

    @field_validator('solution_test', mode='before')
    def validate_solution_test(cls, v, info):
        solution_tolerance = info.data.get('solution_tolerance')
        if solution_tolerance is None and v is not None:
            raise ValueError("solution_test should be None if solution_tolerance is not provided")
        return v

    def __str__(self):
        s = f'tolerance: {self.residual_tolerance}'
        if self.residual_test is not None:
            s += f', test, {self.residual_test}'
            if self.scaling is not None:
                s += f', {self.scaling}'
        if self.solution_tolerance is not None:
            s += f', {self.solution_tolerance}'
            if self.solution_test is not None:
                s += f', test, {self.solution_test}'
        return s

class MaxIterations(MBEntity):
    '''Error out after max_iterations without passing the convergence test. The default value is zero.'''

    max_iterations: int = 0
    optional_keywords: Optional[Literal['at most']] = None

    def __str__(self):
        s = f'max iterations: {self.max_iterations}'
        if self.optional_keywords is not None:
            s += f', {self.optional_keywords}'
        return s

class Method(MBEntity):
    """Base class for every method"""

    @abstractmethod
    def __str__(self) -> str:
        """Has to be overridden to output the MBDyn syntax"""
        pass

class CrankNicolson(Method):
    def __str__(self):
        return 'method: crank nicolson'

class MethodWithRadius(Method):
    # TODO: Remove this relaxed config when all DriveCallers are refactored
    class Config:
        arbitrary_types_allowed = True

    differential_radius: Union[DriveCaller, DriveCaller2]
    algebraic_radius: Optional[Union[DriveCaller, DriveCaller2]] = None
    
    def __str__(self):
        s = f'method: {self.__class__.__name__.lower()}, {self.differential_radius}'
        if self.algebraic_radius is not None:
            s += f', {self.algebraic_radius}'
        return s

class MS(MethodWithRadius):
    """The 'ms' method (also referred to as 'ms2') allows for tuning algorithmic dissipation."""
    pass  # Inherits the behavior from MethodWithRadius

class MS2(MethodWithRadius):
    pass  # Inherits the behavior from MethodWithRadius

class MS3(MethodWithRadius):
    """The 'ms3' method is a three-step method allowing for algorithmic dissipation tuning."""
    pass  # Inherits the behavior from MethodWithRadius

class MS4(MethodWithRadius):
    """The 'ms4' method is a four-step method allowing for algorithmic dissipation tuning."""
    pass  # Inherits the behavior from MethodWithRadius

class Hope(MethodWithRadius):
    """The 'hope' method is a multi-stage method combining Crank-Nicolson and 'ms' methods."""
    pass  # Inherits the behavior from MethodWithRadius

class SS2(MethodWithRadius):
    pass

class SS3(MethodWithRadius):
    pass

class SS4(MethodWithRadius):
    pass

class Bathe(MethodWithRadius):
    pass

class MSSTC3(MethodWithRadius):
    pass

class MSSTC4(MethodWithRadius):
    pass

class MSSTC5(MethodWithRadius):
    pass

class MSSTH3(MethodWithRadius):
    pass

class MSSTH4(MethodWithRadius):
    pass

class MSSTH5(MethodWithRadius):
    pass

class Hybrid(MethodWithRadius):
    default_hybrid_method: Literal['implicit euler', 'crank nicolson', 'ms2', 'hope']
    
    def __str__(self):
        s = f'method: hybrid, {self.default_hybrid_method}, {self.differential_radius}'
        if self.algebraic_radius is not None:
            s += f', {self.algebraic_radius}'
        return s

class DIRK33(Method):
    def __str__(self):
        return 'method: DIRK33'

class DIRK43(Method):
    def __str__(self):
        return 'method: DIRK43'

class DIRK54(Method):
    def __str__(self):
        return 'method: DIRK54'

class BDF(Method):
    order: Optional[Union[int, MBVar]] = None  # 1 or 2

    def __str__(self):
        s = 'method: bdf'
        if self.order is not None:
            s += f', order, {self.order}'
        return s

class ImplicitEuler(Method):
    def __str__(self):
        return 'method: implicit euler'
    
class NonlinearSolver(MBEntity):
    """The nonlinear solver solves a nonlinear problem F (x) = 0."""

    @abstractmethod
    def nonlinear_solver_name(self) -> str:
        """Name of the specific nonlinear solver"""
        pass

    def nonlinear_solver_header(self) -> str:
        """Common syntax for start of any nonlinear solver"""
        return f'nonlinear solver: {self.nonlinear_solver_name()}'
    
class NewtonRaphson(NonlinearSolver):
    pass
    

class MethodforEigenanalysis(MBEntity):
    '''Base class for the methods used in Eigenanalysis'''

    @abstractmethod
    def __str__(self) -> str:
        """Has to be overridden to output the MBDyn syntax"""
        pass

class UseLapack(MethodforEigenanalysis):
    balance: Optional[Literal['no', 'sclae', 'permute', 'all']] = None

    def __str__(self):
        s = 'use lapack'
        if self.balance is not None:
            s += f', balance, {self.balance}'
        return s
    
class UseArpack(MethodforEigenanalysis):
    nev: Union[int, MBVar]
    ncv: Union[int, MBVar]
    tol: Union[float, MBVar]
    max_iter: Optional[Union[int, MBVar]] = 300

    @field_validator('tol')
    def check_tolerance(cls, v):
        if v < 0:
            raise ValueError("Tolerance (tol) must be positive. Use zero for machine precision.")
        return v

    def __str__(self):
        s = f'use arpack, {self.nev}, {self.ncv}, {self.tol}'
        if self.max_iter != 300:
            s += f', max iterations, {self.max_iter}'
        return s

class UseJdqz(MethodforEigenanalysis):
    nev: Union[int, MBVar]
    ncv: Union[int, MBVar]
    tol: Union[float, MBVar]

    @field_validator('tol')
    def check_tolerance(cls, v):
        if v < 0:
            raise ValueError("Tolerance (tol) must be positive. Use zero for machine precision.")
        return v

    def __str__(self):
        return f'use arpack, {self.nev}, {self.ncv}, {self.tol}'

class UseExternal(MethodforEigenanalysis):
    def __str__(self):
        return 'use external'

class Eigenanalysis(MBEntity):
    '''
    Performs the direct eigenanalysis of the problem. This functionality is experimental. Direct 
    eigenanalysis based on the matrices of the system only makes sense when the system is in a 
    steady conﬁguration, so the user needs to ensure this conﬁguration has been reached.
    Moreover, not all elements currently contribute to the Jacobian matrix of the system, so YMMV. In case
    of rotating systems, a steady conﬁguration could be reached when the model is expressed in a relative
    reference frame, using the rigid body kinematics card.
    '''

    # Mode Options Enum for eigenvalue sorting criteria
    class ModeOptions(Enum):
        SMALLEST_MAGNITUDE = "smallest magnitude"
        LARGEST_MAGNITUDE = "largest magnitude"
        LARGEST_REAL_PART = "largest real part"
        SMALLEST_REAL_PART = "smallest real part"
        LARGEST_IMAGINARY_PART = "largest imaginary part"
        SMALLEST_IMAGINARY_PART = "smallest imaginary part"

    num_times: Optional[Union[int, MBVar]] = None
    when: Union[float, MBVar, List[Union[float, MBVar]]]
    suffix_width: Optional[Union[float, MBVar, Literal['compute']]] = None
    suffix_format: Optional[str] = None
    output_full_matrices: Optional[bool] = None
    output_sparse_matrices: Optional[bool] = None
    output_eigenvectors: Optional[bool] = None
    output_geometry: Optional[bool] = None
    matrix_precision: Optional[Union[float, MBVar]] = None
    results_precision: Optional[Union[float, MBVar]] = None
    parameter: Optional[Union[float, MBVar]] = None
    mode_options: Optional[ModeOptions] = None
    lower_frequency_limit: Optional[Union[float, MBVar]] = None
    upper_frequency_limit: Optional[Union[float, MBVar]] = None
    method: Optional[MethodforEigenanalysis] = None

    @model_validator(mode='after')
    def check_when_and_num_times(cls, values):
        when = values.get('when')
        num_times = values.get('num_times')
        if isinstance(when, list) and num_times is None:
            raise ValueError("If 'when' is given as a list, 'num_times' must also be provided.")
        return values

    def add_optional_field(self, s, field_name, field_value):
        if field_value is True:
            return s + f',\n\t{field_name}'
        elif field_value is not None and field_value is not False:
            return s + f',\n\t{field_name}, {field_value}'
        return s

    def __str__(self):
        s = 'eigenanalysis: '
        if isinstance(self.when, List):
            s += f'\n\tlist, {self.num_times}, '
            s += ', '.join(str(i) for i in self.when)
        else:
            s += f'\n\t{self.when}'
        
        s = self.add_optional_field(s, 'suffix width', self.suffix_width)
        s = self.add_optional_field(s, 'suffix format', self.suffix_format)
        s = self.add_optional_field(s, 'output full matrices', self.output_full_matrices)
        s = self.add_optional_field(s, 'output sparse matrices', self.output_sparse_matrices)
        s = self.add_optional_field(s, 'output eigenvectors', self.output_eigenvectors)
        s = self.add_optional_field(s, 'output geometry', self.output_geometry)
        s = self.add_optional_field(s, 'matrix output precision', self.matrix_precision)
        s = self.add_optional_field(s, 'results output precision', self.results_precision)
        s = self.add_optional_field(s, 'parameter', self.parameter)
        s = self.add_optional_field(s, 'mode', self.mode_options)
        s = self.add_optional_field(s, 'lower frequency limit', self.lower_frequency_limit)
        s = self.add_optional_field(s, 'upper frequency limit', self.upper_frequency_limit)
        if self.method is not None:
            s += f',\n\t{self.method}'
        
        return s

        # TODO: Delete these lines of code after review of the new approach from mentor
        # if self.suffix_width is not None:
        #     s += f',\n\tsuffix width, {self.suffix_width}'
        # if self.suffix_format is not None:
        #     s += f',\n\tsuffix format, {self.suffix_format}'
        # if self.output_full_matrices is True:
        #     s += f',\n\toutput full matrices'
        # if self.output_sparse_matrices is True:
        #     s += f',\n\toutput sparse matrices'
        # if self.output_eigenvectors is True:
        #     s += f',\n\toutput eigenvectors'
        # if self.output_geometry is True:
        #     s += f',\n\toutput geometry'
        # if self.matrix_precision is not None:
        #     s += f',\n\tmatrix output precision, {self.matrix_precision}'
        # if self.results_precision is not None:
        #     s += f',\n\tresults output precision, {self.results_precision}'
        # if self.parameter is not None:
        #     s += f',\n\tparameter, {self.parameter}'
        # if self.mode_options is not None:
        #     s += f',\n\tmode, {self.mode_options}'
        # if self.lower_frequency_limit is not None:
        #     s += f',\n\tlower frequency limit, {self.lower_frequency_limit}'
        # if self.upper_frequency_limit is not None:
        #     s += f',\n\tupper frequency limit, {self.upper_frequency_limit}'
        # if self.method is not None:
        #     s += f',\n\t{self.method}'
        # return s


class LinearSolver(MBEntity):
    solver_name: Literal[
        'naive', 'umfpack', 'klu', 'y12', 'lapack', 'superlu', 'taucs', 
        'pardiso', 'pardiso_64', 'watson', 'pastix', 'qr', 'spqr', 
        'aztecoo', 'amesos', 'siconos dense', 'siconos sparse'
    ]

    # General solver settings
    storage_mode: Optional[Literal['map', 'cc', 'dir', 'grad']] = None
    ordering: Optional[Literal['colamd', 'mmdata', 'amd', 'given', 'metis']] = None
    
    # Threading configuration
    multithread: Optional[Literal['mt', 'multithread']] = None
    threads: Optional[Union[int, MBVar]] = None
    
    # Solver-specific parameters
    workspace_size: Optional[Union[int, MBVar]] = None
    pivot_factor: Optional[Union[float, MBVar]] = None
    drop_tolerance: Optional[Union[float, MBVar]] = None
    block_size: Optional[Union[int, MBVar]] = None
    
    # Scaling options
    scale: Optional[Literal[
        'no', 'always', 'once', 'row max', 'row sum', 'column max', 
        'column sum', 'lapack', 'iterative', 'row max column max'
    ]] = None
    scale_tolerance: Optional[Union[float, MBVar]] = None
    scale_max_iter: Optional[Union[int, MBVar]] = None
    
    # Refinement and tolerance settings
    refine_tolerance: Optional[Union[float, MBVar]] = None
    refine_max_iter: Optional[Union[int, MBVar]] = None

    # Preconditioner options
    preconditioner: Optional[Literal[
        'umfpack', 'klu', 'lapack', 'ilut', 'superlu', 'mumps',
        'scalapack', 'dscpack', 'pardiso', 'paraklete', 'taucs', 'csparse'
    ]] = None

    @model_validator(mode="before")
    def check_solver_specific_parameters(cls, values):
        # Check if multithread is set but threads is None
        if values.get('multithread') is not None and values.get('threads') is None:
            raise ValueError("If multithread is set, threads must also be specified.")
        
        solver = values.get('solver_name')
        
        # Check parameters specific to 'umfpack'
        if solver == 'umfpack':
            values.setdefault('block_size', 32)
            if values.get('workspace_size') is not None:
                raise ValueError("workspace_size is ignored for umfpack solver.")
            if values.get('drop_tolerance') is None:
                values['drop_tolerance'] = 0.0  # Default drop tolerance for umfpack

        # Enforce ordering for naive solver
        if solver == 'naive' and values.get('ordering') is None:
            raise ValueError("The naive solver requires an ordering option for robustness, e.g., 'colamd'.")

        # Enforce refine_max_iter for certain solvers
        if solver in ['pardiso', 'pardiso_64', 'pastix'] and values.get('refine_max_iter') is None:
            raise ValueError(f"{solver} requires refine_max_iter for stability.")

        # Enforce ignore of certain parameters for specific solvers
        if solver in ['naive', 'y12', 'lapack'] and values.get('workspace_size') is not None:
            raise ValueError(f"workspace_size is ignored for {solver} solver.")
        
        if solver == 'klu' and values.get('scale') not in [None, 'always', 'once']:
            raise ValueError("KLU solver supports only 'always' or 'once' scale options.")

        # Ensure that iterative refinement settings are consistent
        if solver in ['umfpack', 'pastix'] and values.get('refine_max_iter') and values.get('refine_tolerance') is None:
            raise ValueError("Refinement tolerance is required if refine_max_iter is set.")

        # TODO: Have to check thoroughly 
        # # Check for supported keywords by solvers
        # supported_keywords = {
        #     'umfpack': ['map', 'cc', 'dir', 'drop_tolerance', 'block_size', 'scale', 'refine_max_iter'],
        #     'klu': ['map', 'cc', 'dir', 'scale', 'refine_max_iter'],
        #     'y12': ['map', 'dir'],
        #     'superlu': ['map', 'cc', 'scale'],
        #     'pastix': ['map', 'cc', 'scale', 'refine_max_iter'],
        #     'naive': ['cc', 'scale', 'colamd', 'mmdata'],
        #     'spqr': ['colamd', 'amd', 'metis', 'given'],
        # }

        # if solver in supported_keywords and 'keywords' in values:
        #     invalid_keywords = [kw for kw in values['keywords'] if kw not in supported_keywords[solver]]
        #     if invalid_keywords:
        #         raise ValueError(f"The following keywords are not supported by the {solver} solver: {', '.join(invalid_keywords)}.")

        # Check for pivot factor validity
        if values.get('pivot_factor') is not None:
            if not (0.0 <= values['pivot_factor'] <= 1.0):
                raise ValueError("pivot_factor must be between 0.0 and 1.0.")

        # Check for drop tolerance with unsupported solvers
        if solver != 'umfpack' and values.get('drop_tolerance') is not None:
            raise ValueError("drop_tolerance can only be used with the umfpack solver.")

        # Check for inconsistent scaling options
        if solver not in ['naive', 'klu', 'umfpack', 'pastix'] and values.get('scale') is not None:
            raise ValueError(f"scale option is not supported by the {solver} solver.")

        # Check for valid block size for umfpack
        if solver != 'umfpack' and values.get('block_size') is not None:
            raise ValueError("block_size can only be used with the umfpack solver.")

        return values

    def __str__(self):
        s = f'linear solver: {self.solver_name}'
        if self.storage_mode is not None:
            s += f', {self.storage_mode}'
        if self.ordering is not None:
            s += f', {self.ordering}'
        if self.multithread is not None:
            s += f',\n\t\t{self.multithread}, {self.threads}'
        if self.workspace_size is not None:
            s += f',\n\t\tworkspace size, {self.workspace_size}'
        if self.pivot_factor is not None:
            s += f',\n\t\tpivot factor, {self.pivot_factor}'
        if self.drop_tolerance is not None:
            s += f',\n\t\tdrop tolerance, {self.drop_tolerance}'
        if self.block_size is not None:
            s += f',\n\t\tblock size, {self.block_size}'
        if self.scale is not None:
            s += f',\n\t\tscale, {self.scale}'
            if self.scale_tolerance is not None:
                s += f',\n\t\t\tscale tolerance, {self.scale_tolerance}'
            if self.scale_max_iter is not None:
                s += f',\n\t\t\tscale iterations, {self.scale_max_iter}'
        if self.refine_tolerance is not None:
            s += f',\n\t\ttolerance, {self.refine_tolerance}'
        if self.refine_max_iter is not None:
            s += f',\n\t\tmax iterations, {self.refine_max_iter}'
        if self.preconditioner is not None:
            s += f',\n\t\tpreconditioner, {self.preconditioner}'
        return s
    
class Threads(MBEntity):
    mode: Literal['auto', 'disable', 'assembly', 'solver'] = 'auto'
    threads: Optional[Union[int, MBVar]] = None

    @model_validator(mode='after')
    def check_threads_provided(cls, model):
        mode = model.mode
        threads = model.threads

        if mode in ['assembly', 'solver'] and threads is None:
            raise ValueError("threads must be provided if mode is 'assembly' or 'solver'.")
        elif mode in ['auto', 'disable'] and threads is not None: 
            raise ValueError("threads must be None if mode is 'auto' or 'disable'.")
        return model
    
    def __str__(self):
        s = f'threads: {self.mode}'
        if self.threads:
            s += f', {self.threads}'
        return s

class DerivativesCoefficient(MBEntity):
    coefficient: Optional[Union[float, MBVar]] = None
    is_auto: Optional[bool] = False
    max_iterations: Optional[Union[int, MBVar]] = None
    factor: Optional[Union[float, MBVar]] = None

    @model_validator(mode='before')
    @classmethod
    def validate_auto_case(cls, data: dict):
        is_auto = data.get('is_auto', False)  # Default to False if not provided
        coefficient = data.get('coefficient')
        factor = data.get('factor')
        max_iterations = data.get('max_iterations')

        if not is_auto:
            if coefficient is None:
                raise ValueError("When 'auto' is not selected, a numeric value for 'coefficient' must be specified.")
            if factor is not None or max_iterations is not None:
                raise ValueError("`factor` and `max_iterations` can only be specified when 'auto' is selected.")
        
        return data

    def __str__(self):
        s = 'derivatives coefficient: '
        if self.is_auto:
            s += f"{f'{self.coefficient}, ' if self.coefficient is not None else ''}auto"
        else:
            s += f'{self.coefficient}'
        if self.max_iterations is not None:
            s += f",\n\tmax iterations, {self.max_iterations}"
        if self.factor is not None:
            s += f",\n\tfactor, {self.factor}"
        return s


class OutputSettings(MBEntity):
    items: List[Literal[
        "iterations", "residual", "solution", "jacobian matrix", 
        "messages", "counter", "bailout", "matrix condition number", 
        "solver condition number", "cpu time", "none"
    ]]

    # TODO: Have to get a review
    @model_validator(mode="before")
    @classmethod
    def validate_items(cls, data: dict):
        items = data.get("items", [])
        # Ensure the 'none' keyword is used alone or as the first item
        if "none" in items and items[0] != "none":
            raise ValueError("If 'none' is specified, it must be the first item.")
        return data

    def __str__(self):
        return f"output: {', '.join(self.items)}"

class InitialValue(MBEntity):
    '''
    At present, the main problem is initial value, which solves initial value problems by means of generic
    integration schemes that can be cast in a broad family of multistep and, experimentally, Implicit Runge-
    Kutta-like schemes
    '''

    # TODO: Remove this relaxed config when all DriveCallers are refactored
    model_config = ConfigDict(arbitrary_types_allowed=True)

    initial_time: Union[float, MBVar]
    final_time: Union[float, MBVar, Literal["forever"]]
    strategy: Optional[Union[StrategyChange, StrategyFactor, StrategyNoChange]] = None
    min_time_step: Optional[Union[float, MBVar]] = None
    max_time_step: Optional[Union[float, MBVar, Literal["unlimited"]]] = None
    time_step: Union[float, MBVar]
    tolerance: Tolerance
    max_iterations: MaxIterations
    modify_residual_test: Optional[Union[bool, int]] = False    # 0 / 1 / True / False
    method: Optional[Method] = None
    eigenanalysis: Optional[Eigenanalysis] = None
    linear_solver: Optional[LinearSolver] = None
    threads: Optional[Threads] = None
    derivatives_tolerance: Optional[Union[float, MBVar]] = None
    derivatives_max_iterations: Optional[Union[int, MBVar]] = None
    derivatives_coefficient: Optional[DerivativesCoefficient] = None
    output_settings: Optional[OutputSettings] = None
    output_meter: Optional[Union[DriveCaller, DriveCaller2]] = None

    @field_validator('modify_residual_test')
    def set_modify_residual_test(cls, v):
        if isinstance(v, (int, bool)):
            if v in [0, False]:
                return None
            elif v in [1, True]:
                return "modify residual test"
            else:
                raise ValueError("modify_residual_test must be 0, 1, True, or False.")
        else:
            raise TypeError("modify_residual_test must be of type int or bool.")
        
    def __str__(self):
        s = "begin: initial value;\n"
        s += f"\tinitial time: {self.initial_time};\n"
        s += f"\tfinal time: {self.final_time};\n"
        if self.strategy:
            s += f"\t{self.strategy};\n"
        if self.min_time_step:
            s += f"\tmin time step: {self.min_time_step};\n"
        if self.max_time_step:
            s += f"\tmax time step: {self.max_time_step};\n"
        s += f"\ttime step: {self.time_step};\n"
        s += f"\t{self.max_iterations};\n"
        s += f"\t{self.tolerance};\n"
        if self.modify_residual_test:
            s += f"\tmodify residual test;\n"
        if self.method:
            s += f"\t{self.method};\n"
        if self.eigenanalysis:
            s += f"\t{self.eigenanalysis};\n"
        if self.linear_solver:
            s += f"\t{self.linear_solver};\n"
        if self.threads:
            s += f"\t{self.threads};\n"
        if self.derivatives_tolerance:
            s += f"\tderivatives tolerance: {self.derivatives_tolerance};\n"
        if self.derivatives_max_iterations:
            s += f"\tderivatives max iterations: {self.derivatives_max_iterations};\n"
        if self.derivatives_coefficient:
            s += f"\t{self.derivatives_coefficient};\n"
        if self.output_settings:
            s += f"\t{self.output_settings};\n"
        if self.output_meter:
            s += f"\toutput meter: {self.output_meter};\n"
        s += "end: initial value;\n\n"
        return s

# Control Data
# TODO: Remove these codes as they are temporarily copied here

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
    # TODO: Remove this relaxed config when all DriveCallers are refactored
    class Config:
        arbitrary_types_allowed = True

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

    # TODO: Remove this relaxed config when all DriveCallers are refactored
    class Config:
        arbitrary_types_allowed = True

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
    plates: Optional[Union[int, str]] = None # Not present in the manual, but present in CrankPanel_v2.mbd
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
        if self.plates:   # Not present in the manual, but present in CrankPanel_v2.mbd
            s += f'\tplates: {self.plates};\n'
        if self.solids:
            s += f'\tsolids: {self.solids};\n'
        if self.surface_loads:
            s += f'\tsurface loads: {self.surface_loads};\n'
        if self.rigid_bodies:
            s += f'\trigid bodies: {self.rigid_bodies};\n'

        s += 'end: control data;\n\n'
        return s