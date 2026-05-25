from manim import *
import numpy as np
import warnings
from scipy import signal
import sympy as sp
from collections import OrderedDict
from manim import TexTemplate
from scipy.interpolate import interp1d 

my_template = TexTemplate()
my_template.add_to_preamble(r"\usepackage{amsmath}")  # Add required packages

class PoleZeroMap(VGroup):
    def __init__(self, system, x_range=None, y_range=None, dashed_axis=False, 
                 y_axis_label=None, x_axis_label=None,
                 font_size_labels=28, markers_size=0.15, use_math_tex_labels=True, **kwargs):
        """
        Generates a pole-zero map as a Manim VGroup for continuous- or discrete-time systems.

        This class takes a symbolic transfer function (numerator and denominator) and visualizes
        its poles and zeros in the complex plane. It supports customizable axes, automatic
        scaling, optional unit circle display (for discrete-time systems), and labeled axes.

        PARAMETERS
        ----------
        system : various
            System representation, which can be one of:
            - scipy.signal.lti or transfer function coefficients (list/tuple of arrays)
            - Symbolic expressions for numerator/denominator (using 's' as variable)
            - Tuple of (numerator_expr, denominator_expr) as strings or sympy expressions
        x_range : list[float] | None
            Range for the real axis in the form [min, max, step]. If None, automatically determined.
        y_range : list[float] | None
            Range for the imaginary axis in the form [min, max, step]. If None, automatically determined.
        dashed_axis : bool
            Whether the axis lines are dashed
        x_axis_label : str
            Label for the real axis.
        y_axis_label : str
            Label for the imaginary axis.
        font_size_labels : int
            Font size for axis labels (default: 28).
        show_unit_circle : bool
            Whether to show the unit circle (used for analyzing discrete-time systems).
        **kwargs : Any
            Additional keyword arguments passed to the VGroup constructor.

        RETURNS
        -------
        VGroup
            A Manim VGroup containing the complex axis, poles, zeros, optional unit circle, and tick labels.
        """
        super().__init__(**kwargs)
        self.raw_system = system 
        self.system = self._parse_system_input(system)
        self.x_range = x_range
        self.y_range = y_range
        self.y_axis_label = y_axis_label
        self.x_axis_label = x_axis_label
        self.font_size_labels = font_size_labels
        self.markers_size = markers_size
        self.use_math_tex_labels = use_math_tex_labels

        # Initialize components
        self.axis = None
        self.zeros = None
        self.poles = None
        self.stable = None
        self.unstable = None
        self.unit_circle = None
        self.axis_labels = None
        self.title_text = None
        self.dashed_axes = dashed_axis
        self.tick_style = {
            "color": WHITE,
            "stroke_width": 1.2
        }
        # Create the plot
        self._determine_system_type()
        if self.y_axis_label == None:
            if self.system_type== 'discrete':
                self.y_axis_label = "\\mathrm{Im}(z)"
            else:
                self.y_axis_label = "\\mathrm{Im}(s)"
        
        if self.x_axis_label == None:
            if self.system_type== 'discrete':
                self.x_axis_label = "\\mathrm{Re}(z)"
            else:
                self.x_axis_label = "\\mathrm{Re}(s)"

        self._calculate_poles_zeros()
        self._auto_determine_ranges()
        self._create_plot_components()
        
    def _parse_system_input(self, system):
        """Parse different input formats into numerator and denominator coefficients."""
        # If system is already in (num, den) coefficient form
        if isinstance(system, (tuple, list)) and len(system) == 2:
            if all(isinstance(x, (list, tuple, np.ndarray)) for x in system):
                return system  # Already in coefficient form

        # Handle symbolic expressions
        if isinstance(system, sp.Basic):
            return self._symbolic_to_coefficients(system)

        # Handle string input
        if isinstance(system, str):
            if '/' in system:
                num_str, den_str = system.split('/', 1)
                return self._symbolic_to_coefficients(num_str.strip(), den_str.strip())
            return self._symbolic_to_coefficients(system.strip())

        # Handle (numerator, denominator) as symbolic expressions
        if isinstance(system, (tuple, list)) and len(system) == 2:
            num, den = system
            return self._symbolic_to_coefficients(num, den)

        raise ValueError(f"Unsupported system format: {type(system)}")

    def _symbolic_to_coefficients(self, num_expr, den_expr=1):
        """Convert symbolic expressions to polynomial coefficients."""
        # Determine variable from expressions (s or z)
        expr_str = str(num_expr) + str(den_expr)
        if 's' in expr_str:
            var = sp.symbols('s')
        elif 'z' in expr_str:
            var = sp.symbols('z')
        else:
            var = sp.symbols('s')  # Default to continuous-time

        # Handle complete transfer function expression
        if den_expr == 1 and isinstance(num_expr, sp.Basic):
            frac = sp.fraction(num_expr)
            num_expr = frac[0]
            den_expr = frac[1] if len(frac) > 1 else 1

        # Convert strings to sympy expressions
        if isinstance(num_expr, str):
            num_expr = sp.sympify(num_expr.replace('^', '**'))
        if isinstance(den_expr, str):
            den_expr = sp.sympify(den_expr.replace('^', '**'))

        # Convert to polynomial coefficients
        num_poly = sp.Poly(num_expr, var)
        den_poly = sp.Poly(den_expr, var)

        return (
            [float(c) for c in num_poly.all_coeffs()],
            [float(c) for c in den_poly.all_coeffs()]
        )

    def _determine_system_type(self):
        """Determine if system is continuous (s) or discrete (z) time."""
        if hasattr(self, 'system_type'):  # Already determined
            return

        # Check the original system input for variables
        if isinstance(self.raw_system, str):
            if 'z' in self.raw_system:
                self.system_type = 'discrete'
            else:
                self.system_type = 'continuous'
        elif isinstance(self.raw_system, sp.Basic):
            if 'z' in str(self.raw_system):
                self.system_type = 'discrete'
            else:
                self.system_type = 'continuous'
        elif isinstance(self.raw_system, (tuple, list)) and len(self.raw_system) == 2:
            num, den = self.raw_system
            if any('z' in str(x) for x in [num, den] if isinstance(x, (str, sp.Basic))):
                self.system_type = 'discrete'
            else:
                self.system_type = 'continuous'
        else:
            # Default to continuous-time for coefficient arrays
            self.system_type = 'continuous'

        self.variable = sp.symbols('z') if self.system_type == 'discrete' else sp.symbols('s')

    def _calculate_poles_zeros(self):
        """Calculate poles and zeros from the system representation."""
        num, den = self.system
        
        # Convert coefficients to polynomials
        num_poly = np.poly1d(num)
        den_poly = np.poly1d(den)
        
        # Calculate roots
        zeros = num_poly.r
        poles = den_poly.r
        
        # Convert to coordinate pairs
        self.zero_coords = [(z.real, z.imag) for z in zeros]
        self.pole_coords = [(p.real, p.imag) for p in poles]
        
        # Extract real and imaginary parts
        self.zero_real_parts = [z[0] for z in self.zero_coords]
        self.zero_imag_parts = [z[1] for z in self.zero_coords]
        self.pole_real_parts = [p[0] for p in self.pole_coords]
        self.pole_imag_parts = [p[1] for p in self.pole_coords]
    
    def _auto_determine_ranges(self):
        """Determine the x and y ranges if not specified"""
        # Calculate max and min for real and imaginary parts
        max_zero_real = max(self.zero_real_parts) if self.zero_real_parts else 0
        min_zero_real = min(self.zero_real_parts) if self.zero_real_parts else 0
        max_zero_imag = max(self.zero_imag_parts) if self.zero_imag_parts else 0
        min_zero_imag = min(self.zero_imag_parts) if self.zero_imag_parts else 0

        max_pole_real = max(self.pole_real_parts) if self.pole_real_parts else 0
        min_pole_real = min(self.pole_real_parts) if self.pole_real_parts else 0
        max_pole_imag = max(self.pole_imag_parts) if self.pole_imag_parts else 0
        min_pole_imag = min(self.pole_imag_parts) if self.pole_imag_parts else 0
        
        # Determine x_range
        if self.x_range is None:
            x_range_max = max(max_zero_real, max_pole_real)
            x_range_min = min(min_zero_real, min_pole_real)
            x_total_range = abs(x_range_max - x_range_min)
            self.x_step = max(0.1, min(10.0, (x_total_range+2) / 4))
            self.x_range = [x_range_min-1, x_range_max+1, self.x_step]
        else:
            x_range_max = self.x_range[1]
            x_range_min = self.x_range[0]
            if self.x_range[2] is None:
                x_total_range = abs(x_range_max - x_range_min)
                self.x_step = max(0.1, min(10.0, (x_total_range+2) / 4))
            else:
                self.x_step = self.x_range[2]
        # Determine y_range
        if self.y_range is None:
            y_range_max = max(max_zero_imag, max_pole_imag)
            y_range_min = min(min_zero_imag, min_pole_imag)
            y_total_range = abs(y_range_max - y_range_min)
            self.y_step = max(0.1, min(10.0, (y_total_range+2) / 4))
            self.y_range = [y_range_min-1, y_range_max+1, self.y_step]
        else:
            y_range_max = self.y_range[1]
            y_range_min = self.y_range[0]
            if self.y_range[2] is None:
                y_total_range = abs(y_range_max - y_range_min)
                self.y_step = max(0.1, min(10.0, (y_total_range+2)/ 4))
            else:
                self.y_step = self.y_range[2]
        

    
    def _create_plot_components(self):
        """Create all the visual components of the pole-zero plot"""
        # Create axis

        self.axis = ComplexPlane(
            x_range=self.x_range,
            y_range=self.y_range,
            y_length=6, x_length=10,
            background_line_style={
                "stroke_color": GREY,
                "stroke_width": 1,
                "stroke_opacity": 0
            },
            axis_config={
                "stroke_width": 0,
                "include_ticks": False,
                "include_tip": False
            },
        )
        x_start, x_end = self.axis.x_axis.get_start(), self.axis.x_axis.get_end()
        y_start, y_end = self.axis.y_axis.get_start(), self.axis.y_axis.get_end()

        if self.dashed_axes==True:
            self.x_axis = DashedLine(x_start,x_end, dash_length=0.05, color=WHITE, stroke_opacity=0.7)
            self.y_axis = DashedLine(y_start,y_end, dash_length=0.05, color=WHITE, stroke_opacity=0.7)
        else:
            self.x_axis = Line(x_start,x_end, color=WHITE, stroke_width=1, stroke_opacity=0.7)
            self.y_axis = Line(y_start,y_end, color=WHITE, stroke_width=1,stroke_opacity=0.7)

        self.box = SurroundingRectangle(self.axis, buff=0, color=WHITE, stroke_width=2)
        # Add axis labels
        if self.use_math_tex_labels ==True:
            re_label = MathTex(self.x_axis_label, font_size=self.font_size_labels).next_to(self.box, DOWN, buff=0.55)
            im_label = MathTex(self.y_axis_label, font_size=self.font_size_labels).rotate(PI/2).next_to(self.box, LEFT, buff=0.55)
        else:
            re_label = Text(self.x_axis_label, font_size=self.font_size_labels).next_to(self.box, DOWN, buff=0.55)
            im_label = Text(self.y_axis_label, font_size=self.font_size_labels).rotate(PI/2).next_to(self.box, LEFT, buff=0.55)
        self.axis_labels = VGroup(re_label, im_label)
        self.axis.add(self.axis_labels)
        
        # Plot zeros (blue circles)
        zero_markers = [
            Circle(radius=self.markers_size, color=BLUE, stroke_width=8).move_to(self.axis.n2p(complex(x, y))) 
            for x, y in self.zero_coords
        ]
        self.zeros = VGroup(*zero_markers)
        
        # Plot poles (red crosses)
        pole_markers = [
            Cross(scale_factor=self.markers_size, color=RED, stroke_width=12).move_to(self.axis.n2p(complex(x, y))) 
            for x, y in self.pole_coords
        ]
        self.poles = VGroup(*pole_markers)
        
        self.x_ticks = self._create_ticks(self.axis, orientation="horizontal")
        self.y_ticks = self._create_ticks(self.axis, orientation="vertical")
        self.x_tick_labels = self._create_tick_labels(self.axis, orientation="horizontal")
        self.y_tick_labels = self._create_tick_labels(self.axis, orientation="vertical")  

        # Add all components to the group
        self.add(self.axis, self.zeros, self.poles, self.box, self.x_axis, self.y_axis, 
                 self.x_ticks, self.y_ticks, self.x_tick_labels,self.y_tick_labels)
        self.basecomponents = VGroup(self.axis, self.box, self.x_axis, self.y_axis, 
                 self.x_ticks, self.y_ticks, self.x_tick_labels,self.y_tick_labels)
        
        if self.system_type == 'discrete':
            x_min, x_max = self.axis.x_range[0], self.axis.x_range[1]
            r=1
            if (r < x_min) or (r < -x_max):
                self.unit_circle = VGroup()
            else:
                t_left = np.arccos(np.clip(x_max / r, -1, 1)) if x_max < r else 0
                t_right = np.arccos(np.clip(x_min / r, -1, 1)) if x_min > -r else np.pi
                t_ranges = [
                [t_left, t_right],
                [2 * np.pi - t_right, 2 * np.pi - t_left]
                ]
                unit_circle_parts = VGroup()
                for t_start, t_end in t_ranges:
                    if t_end > t_start:  # Only add if the arc is valid
                        part = ParametricFunction(
                            lambda t: self.axis.number_to_point(np.exp(1j*t)),
                            t_range=[t_start, t_end],
                            color=WHITE,
                            stroke_width=1.5,
                            stroke_opacity=0.7,
                        )
                        unit_circle_parts.add(part)
                        unit_circle_solid = unit_circle_parts
                        self.unit_circle=unit_circle_solid
                    
        else:
            self.unit_circle = VGroup()
        self.add(self.unit_circle)
        self.basecomponents.add(self.unit_circle)

    def _create_tick_labels(self, axes, orientation="horizontal"):
        """Create tick labels using c2p method"""
        labels = VGroup()
        
        if orientation == "horizontal":
            # X-axis labels (bottom only)
            step = self.x_step
            values = np.arange(
                self.x_range[0],
                self.x_range[1]+step/6,
                step
            )

            for x_val in values:
                point = axes.c2p(x_val, axes.y_range[0])
                label_text = f"{x_val:.1f}"
                label = MathTex(label_text, font_size=18)
                label.move_to([point[0], point[1] - 0.3, 0])  # Position below axis
                labels.add(label)
                
        else:  # vertical (y-axis labels - left only)
            step = self.y_step
            values = np.arange(
                self.y_range[0],
                self.y_range[1]+step/5,
                step
            )

            for y_val in values:
                point = axes.c2p(axes.x_range[0], y_val)
                label_text = f"{y_val:.1f}"
                label = MathTex(label_text, font_size=18)
                label.move_to([point[0] - 0.3, point[1], 0])  # Position left of axis
                labels.add(label)
        
        return labels
    
    def _create_ticks(self, axes, orientation="horizontal"):
        """Generalized tick creation for both axes using c2p method"""
        ticks = VGroup()
        tick_length = 0.1
        
        if orientation == "horizontal":
            # For x-axis ticks (top and bottom)
            step = self.x_step
            values = np.arange(
                self.x_range[0],
                self.x_range[1],
                step
            )

            for x_val in values:
                # Bottom ticks
                bottom_point = axes.c2p(x_val, axes.y_range[0])
                ticks.add(Line(
                    [bottom_point[0], bottom_point[1], 0],
                    [bottom_point[0], bottom_point[1] + tick_length, 0],
                    **self.tick_style
                ))
                
                # Top ticks
                top_point = axes.c2p(x_val, axes.y_range[1])
                ticks.add(Line(
                    [top_point[0], top_point[1] - tick_length, 0],
                    [top_point[0], top_point[1], 0],
                    **self.tick_style
                ))
                
        else:  # vertical (y-axis ticks - left and right)
            step = self.y_step
            values = np.arange(
                self.y_range[0],
                self.y_range[1],
                step
            )

            for y_val in values:
                # Left ticks
                left_point = axes.c2p(axes.x_range[0], y_val)
                ticks.add(Line(
                    [left_point[0], left_point[1], 0],
                    [left_point[0] + tick_length, left_point[1], 0],
                    **self.tick_style
                ))
                
                # Right ticks
                right_point = axes.c2p(axes.x_range[1], y_val)
                ticks.add(Line(
                    [right_point[0] - tick_length, right_point[1], 0],
                    [right_point[0], right_point[1], 0],
                    **self.tick_style
                ))
        
        return ticks
    
    def add_stability_regions(self, show_stable=True, show_unstable=True, stable_label="Stable", unstable_label="Unstable"
                              , stable_color=BLUE, unstable_color=RED, use_mathtex = False, fill_opacity=0.2, label_font_size = 30, add_directly=True):
        """Create the stability regions based on system type"""
        if self.system_type == 'continuous':
            # Highlight unstable region (right-half plane)
            if self.x_range[1] > 0:
                right_edge = self.axis.c2p(self.x_range[1], 0)[0]  # Get x-coordinate of right edge
                left_edge = self.axis.c2p(0, 0)[0]  # Get x-coordinate of y-axis
            
                width_unst = right_edge - left_edge
                height_unst = abs(self.axis.c2p(0, self.y_range[1])[1] - self.axis.c2p(0, self.y_range[0])[1])
            
                self.unstable_region = Rectangle(
                    width=width_unst, 
                    height=height_unst,
                    color=unstable_color, 
                    fill_opacity=fill_opacity, 
                    stroke_opacity=0
                ).move_to(
                self.axis.n2p(complex(self.x_range[1]/2, 0))  # Center in the unstable region
                )
                if use_mathtex==True:
                    self.text_unstable = MathTex(unstable_label, font_size=label_font_size).move_to(self.unstable_region, aligned_edge=UP).shift(0.2*DOWN)
                else:
                    self.text_unstable = Text(unstable_label, font_size=label_font_size).move_to(self.unstable_region, aligned_edge=UP).shift(0.2*DOWN)
                
                if width_unst <= 2:
                    self.text_unstable.shift(RIGHT)
                
                self.unstable = VGroup(self.unstable_region, self.text_unstable)
                if show_unstable == True and add_directly==True:
                    self.add(self.unstable)
            
            # Highlight stable region (left-half plane)
            if self.x_range[0] < 0:
                left_edge = self.axis.c2p(self.x_range[0], 0)[0]  # Get x-coordinate of left edge
                right_edge = self.axis.c2p(0, 0)[0]  # Get x-coordinate of y-axis
                
                width_st = right_edge - left_edge
                height_st = abs(self.axis.c2p(0, self.y_range[1])[1] - self.axis.c2p(0, self.y_range[0])[1])
                
                self.stable_region = Rectangle(
                    width=width_st, 
                    height=height_st,
                    color=stable_color, 
                    fill_opacity=fill_opacity, 
                    stroke_opacity=0
                ).move_to(
                    self.axis.n2p(complex(self.x_range[0]/2, 0))  # Center in the stable region
                )
                
                if use_mathtex==True:
                    self.text_stable = MathTex(stable_label, font_size=label_font_size).move_to(self.stable_region, aligned_edge=UP).shift(0.2*DOWN)
                else:
                    self.text_stable = Text(stable_label, font_size=label_font_size).move_to(self.stable_region, aligned_edge=UP).shift(0.2*DOWN)
                if width_st <= 2:
                    self.text_stable.shift(0.2*LEFT)
                
                self.stable = VGroup(self.stable_region, self.text_stable)
                if show_stable==True and add_directly==True:
                    self.add(self.stable)

        
        elif self.system_type == 'discrete':
            
            # Stable region (inside unit circle)
            x_min, x_max = self.axis.x_range[0], self.axis.x_range[1]
            r=1
            if (r < x_min) or (r < -x_max):
                self.stable_region = VGroup()
            else:
                t_left = np.arccos(np.clip(x_max / r, -1, 1)) if x_max < r else 0
                t_right = np.arccos(np.clip(x_min / r, -1, 1)) if x_min > -r else np.pi
                t_ranges = [
                [t_left, t_right],
                [2 * np.pi - t_right, 2 * np.pi - t_left]
                ]
                unit_circle_parts = VGroup()
                for t_start, t_end in t_ranges:
                    if t_end > t_start:  # Only add if the arc is valid
                        part = ParametricFunction(
                            lambda t: self.axis.number_to_point(np.exp(1j*t)),
                            t_range=[t_start, t_end],
                            color=WHITE,
                            stroke_width=1.5,
                            stroke_opacity=0,
                            fill_opacity=fill_opacity,
                            fill_color = stable_color
                        )
                        unit_circle_parts.add(part)
                        unit_circle_solid = unit_circle_parts
                        self.stable_region=unit_circle_solid
            if use_mathtex==False:
                self.text_stable = Text(stable_label, font_size=label_font_size).move_to(self.stable_region, aligned_edge=UP)
            else:
                self.text_stable = MathTex(stable_label, font_size=label_font_size).move_to(self.stable_region, aligned_edge=UP)

            self.text_stable.shift(0.5*UP)
            self.stable = VGroup(self.stable_region, self.text_stable)

            if show_stable == True and add_directly==True:
                self.add(self.stable)
            
            # Unstable region (outside unit circle)
            x_min, x_max = self.axis.x_range[0], self.axis.x_range[1]
            y_min, y_max = self.axis.y_range[0], self.axis.y_range[1]
            
            # Create a rectangle covering the whole axis
            full_rect = Rectangle(
                width=self.axis.get_x_axis().length,
                height=self.axis.get_y_axis().length,
                color=unstable_color,
                fill_opacity=fill_opacity,
                stroke_opacity=0
            ).align_to(self.box, RIGHT)

            subtraction_circle = Circle( 
                radius=1,  # Unit circle to be stretched later
                color=unstable_color,
                fill_opacity=0,
                stroke_opacity=0
            )

            # Move to the origin in data space
            subtraction_circle.move_to(self.axis.n2p(0 + 0j))

            visual_unit_x_length = self.axis.x_axis.get_unit_size()
            visual_unit_y_length = self.axis.y_axis.get_unit_size()

            # Scale the unit circle so its visual radius is 1 unit in axis coordinates
            subtraction_circle.scale(np.array([visual_unit_x_length, visual_unit_y_length, 1]),
                                    about_point=self.axis.n2p(0 + 0j))

            # Subtract the unit circle from the full rectangle
            self.unstable_region = Difference(
                full_rect,
                subtraction_circle, 
                color=unstable_color,
                fill_opacity=fill_opacity,
                stroke_opacity=0
            )
            if use_mathtex==False:    
                self.text_unstable = Text(unstable_label, font_size=label_font_size)
            else:
                self.text_unstable = MathTex(unstable_label, font_size=label_font_size)
            self.text_unstable.align_to(full_rect, UP + LEFT)
            self.text_unstable.shift(0.4 * DOWN + 0.4 * RIGHT)
            self.unstable = VGroup(self.unstable_region, self.text_unstable)
            if show_unstable==True and add_directly==True:
                self.add(self.unstable)
            self.unstable_region.set_z_index(-1)  # Send to background
            self.stable_region.set_z_index(-1)  # Bring stable region to fron
            
        return self
    def title(self, text, font_size=25, color=WHITE, use_math_tex=False):
        """
        Add or update the title of the pole-zero plot.
        
        PARAMETERS
        ----------

        text : str
            The title text
        font_size : float
            Font size of the title
        color : Manim color
            Color of the title
        use_math_tex : bool
            Whether to render as MathTex
        """
        # Remove existing title if present
        if self.title_text in self:
            self.remove(self.title_text)
        
        # Create new title
        if use_math_tex:
            self.title_text = MathTex(text, font_size=font_size, color=color)
        else:
            self.title_text = Text(text, font_size=font_size, color=color)
        
        # Position the title
        self.title_text.next_to(self.axis, UP, buff=0.2)
        self.add(self.title_text)
        self.basecomponents.add(self.title_text)
        return self

    def scale(self, scale_factor, **kwargs):
        """
        Scale the PoleZeroMap group, ensuring stroke widths of components (markers, axes, box, ticks)
        are scaled proportionally.
        """
        super().scale(scale_factor, **kwargs)
        def scale_stroke(mob, factor):
            if hasattr(mob, "get_stroke_width") and hasattr(mob, "set_stroke"):
                mob.set_stroke(width=mob.get_stroke_width() * factor)
            for sub in mob.submobjects:
                scale_stroke(sub, factor)
        scale_stroke(self, scale_factor)
        return self