from manim import *
import numpy as np
import warnings
from scipy import signal
import sympy as sp
from scipy.interpolate import interp1d

class SystemResponse:
    def __init__(self, system, response_type="step", method="numerical", time_limit=10.0):
        self.raw_system = system
        self.response_type = response_type
        self.method = method
        self.time_limit = time_limit
        
        self.s = sp.symbols('s')
        self.t = sp.symbols('t', real=True)
        
        self._initialize_response()

    def _initialize_response(self):
        # Parse system into a sympy expression
        if isinstance(self.raw_system, str):
            if '/' in self.raw_system:
                num_str, den_str = self.raw_system.split('/', 1)
                num_expr = sp.sympify(num_str.strip().replace('^', '**'))
                den_expr = sp.sympify(den_str.strip().replace('^', '**'))
                self.expr = num_expr / den_expr
            else:
                self.expr = sp.sympify(self.raw_system.strip().replace('^', '**'))
        elif isinstance(self.raw_system, sp.Basic):
            self.expr = self.raw_system
        elif isinstance(self.raw_system, (tuple, list)) and len(self.raw_system) == 2:
            num, den = self.raw_system
            if isinstance(num, (list, tuple, np.ndarray)):
                num_poly = sum(c * self.s**i for i, c in enumerate(reversed(num)))
                den_poly = sum(c * self.s**i for i, c in enumerate(reversed(den)))
                self.expr = num_poly / den_poly
            else:
                num_expr = sp.sympify(str(num).replace('^', '**'))
                den_expr = sp.sympify(str(den).replace('^', '**'))
                self.expr = num_expr / den_expr
        elif isinstance(self.raw_system, (signal.TransferFunction, signal.lti)):
            num = self.raw_system.num
            den = self.raw_system.den
            num_poly = sum(c * self.s**i for i, c in enumerate(reversed(num)))
            den_poly = sum(c * self.s**i for i, c in enumerate(reversed(den)))
            self.expr = num_poly / den_poly
        else:
            raise ValueError(f"Unsupported system format: {type(self.raw_system)}")

        # Setup calculation method
        if self.method == "symbolic":
            if self.response_type == "step":
                Y = self.expr / self.s
            else:
                Y = self.expr
            
            try:
                self.symbolic_response = sp.inverse_laplace_transform(Y, self.s, self.t)
                # Identify any symbolic parameters (like m, c, k) other than t
                self.extra_symbols = list(self.symbolic_response.free_symbols - {self.t})
                self.eval_func = sp.lambdify([self.t] + self.extra_symbols, self.symbolic_response, modules=['numpy', 'sympy'])
            except Exception as e:
                warnings.warn(f"Symbolic inverse Laplace failed: {e}. Falling back to numerical method.", UserWarning)
                self.method = "numerical"
                self._setup_numerical()
        else:
            self._setup_numerical()

    def _setup_numerical(self):
        try:
            num_poly = sp.Poly(sp.numerator(self.expr), self.s)
            den_poly = sp.Poly(sp.denominator(self.expr), self.s)
            num_coeffs = [float(c) for c in num_poly.all_coeffs()]
            den_coeffs = [float(c) for c in den_poly.all_coeffs()]
            self.sys_tf = signal.TransferFunction(num_coeffs, den_coeffs)
        except Exception as e:
            raise ValueError(f"For numerical calculation, system must not contain free variables other than 's': {e}")

        t_span = np.linspace(0, self.time_limit, 1000)
        if self.response_type == "step":
            self.t_data, self.y_data = signal.step(self.sys_tf, T=t_span)
        else:
            self.t_data, self.y_data = signal.impulse(self.sys_tf, T=t_span)
        
        self.interp_func = interp1d(self.t_data, self.y_data, bounds_error=False, fill_value=(self.y_data[0], self.y_data[-1]))

    def __call__(self, t_val, **kwargs):
        if self.method == "symbolic":
            args = [t_val]
            for sym in self.extra_symbols:
                sym_name = str(sym)
                if sym_name in kwargs:
                    args.append(kwargs[sym_name])
                else:
                    raise ValueError(f"Symbolic parameter '{sym_name}' must be provided as a keyword argument.")
            return float(self.eval_func(*args))
        else:
            return float(self.interp_func(t_val))

class StepResponse(SystemResponse):
    def __init__(self, system, method="numerical", time_limit=10.0):
        super().__init__(system, response_type="step", method=method, time_limit=time_limit)

class ImpulseResponse(SystemResponse):
    def __init__(self, system, method="numerical", time_limit=10.0):
        super().__init__(system, response_type="impulse", method=method, time_limit=time_limit)
