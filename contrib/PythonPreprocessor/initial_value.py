from abc import ABC, abstractmethod
from MBDynLib import *

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
    def validate_scaling(cls, v):
        if cls.residual_test is None and v is not None:
            raise ValueError("scaling should be None if residual_test is not provided")
        if v.lower() != 'scale':
            raise ValueError("scaling must be a string literal: 'scale'")
        return v.lower()
    
    @field_validator('solution_test', mode='before')
    def validate_solution_test(cls, v):
        if cls.solution_tolerance is None and v is not None:
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

class MaxIterations(MBEntity):
    '''Error out after max_iterations without passing the convergence test. The default value is zero.'''

    max_iterations: int = 0
    optional_keywords: Optional[Literal['at most']] = None

    def __str__(self):
        s = f'max iterations: {self.max_iterations}'
        if self.optional_keywords is not None:
            s += f', {self.optional_keywords}'
        return s

# class Method(MBEntity):
#     """Base class for every methods"""

#     @abstractmethod
#     def __str__(self) -> str:
#         """Has to be overridden to output the MBDyn syntax"""
#         pass

# class CrankNikson(Method):
#     def __str__(self):
#         s = 'method: crank nikson'
#         return s

# class MS(Method):
#     '''
#     The 'ms' method is proved to be more accurate at high values of asymptotic radius (low dissipation),
#     while the 'hope' method is proved to be more accurate at low values of the radius (high dissipation). They look
#     nearly equivalent at radii close to 0.4, with the former giving the best compromise between algorithmic
#     dissipation and accuracy at about 0.6.
#     '''

#     differential_radius: Union[DriveCaller, DriveCaller2]
#     algebraic_radius: Optional[Union[DriveCaller, DriveCaller2]] = None

#     def __str__(self):
#         s = f'method: ms, {self.differential_radius}'
#         if self.algebraic_radius is not None:
#             s += f', {self.algebraic_radius}'
#         return s

# class Hope(Method):
#     '''
#     The 'ms' method is proved to be more accurate at high values of asymptotic radius (low dissipation),
#     while the 'hope' method is proved to be more accurate at low values of the radius (high dissipation). They look
#     nearly equivalent at radii close to 0.4, with the former giving the best compromise between algorithmic
#     dissipation and accuracy at about 0.6.
#     '''

#     differential_radius: Union[DriveCaller, DriveCaller2]
#     algebraic_radius: Optional[Union[DriveCaller, DriveCaller2]] = None

#     def __str__(self):
#         s = f'method: hope, {self.differential_radius}'
#         if self.algebraic_radius is not None:
#             s += f', {self.algebraic_radius}'
#         return s
    
# class ThirdOrder(Method):
#     '''
#     This method is experimental. It is a third-order, two stage unconditionally stable method,
#     which can be tuned to give the desired algorithmic dissipation by setting the value of the asymptotic
#     spectral radius, which should not be too close to zero. Currently it is not possible to independently set
#     the radius for the differential and the algebraic variables.
#     '''

#     differential_radius: Union[DriveCaller, DriveCaller2, Literal['ad hoc']]

#     def __str__(self):
#         s = f'method: third order, {self.differential_radius}'
#         return s
    
# class BFD(Method):
#     order: Optional[Union[int, MBVar]] = None # 1 / 2
#     '''only first order (implicit Euler) and second order formulas are currently implemented, and the
#     default is the second order formula, which is the most useful'''

#     def __str__(self):
#         s = 'method: bfd'
#         if self.order is not None:
#             s += f', order, {self.order}'
#         return s

# class ImplicitEuler(Method):
#     def __str__(self):
#         s = 'method: implicit euler'
#         return s

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
    

class InitialValue(MBEntity):
    '''
    At present, the main problem is initial value, which solves initial value problems by means of generic
    integration schemes that can be cast in a broad family of multistep and, experimentally, Implicit Runge-
    Kutta-like schemes
    '''

    initial_time: Union[float, MBVar]
    final_time: Union[float, MBVar, str]
    strategy: Optional[Union[StrategyChange, StrategyFactor, StrategyNoChange]] = None
    min_time_step: Optional[Union[float, MBVar]] = None
    max_time_step: Optional[Union[float, MBVar]] = None
    time_step: Union[float, MBVar]
    tolerance: Tolerance
    max_iterations: MaxIterations
    modify_residual_test: Optional[Union[bool, int]] = False    # 0 / 1 / True / False
    method: Method

    @field_validator('modify_residual_test', mode='after')
    def set_modify_residual_test(cls, v):
        if isinstance(v, int) or isinstance(v, bool):
            if v == 0 or v == False:
                return None
            elif v == 1 or v == True:
                return "modify residual test"
            else:
                raise ValueError("modify_residual_test has to be an int: 0 / 1, or a bool: True / False")

