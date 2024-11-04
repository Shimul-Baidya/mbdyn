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
