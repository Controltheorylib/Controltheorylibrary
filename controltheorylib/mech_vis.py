from manim import *
import numpy as np
import warnings

# Spring function
def spring(start=ORIGIN, end=UP * 3, num_coils=6, coil_width=0.4, type="zigzag", **kwargs):
    """
    Generates a spring shape as a Manim VGroup between two points.

    PARAMETERS
    ----------
    start : np.ndarray
        The start point of the spring.
    end : np.ndarray
        The end point of the spring.
    num_coils : int
        Number of coils in the spring. Must be a positive integer.
    coil_width : float
        Width of the coils.
    type : str
        Type of spring shape to generate: either "zigzag" or "helical".
    color : Color
        Color of the spring.
    **kwargs : Any
        Additional parameters passed to Manim's Line and VMobject constructors.

    RETURNS
    -------
    VGroup
        A Manim VGroup containing the constructed spring.
    """

    # Validate parameters
    if num_coils<=0:
        warnings.warn("num_coils must be a positive value, setting to default value (6)", UserWarning)
        num_coils=6

    if coil_width<=0:
        warnings.warn("coild_width must be a positive value, setting to default value (0.5)", UserWarning)
        coil_width=0.5
    
    if type not in ["zigzag", "helical"]:
        warnings.warn("Invalid spring type, setting to default ('zigzag')", UserWarning)
        type = "zigzag"

    # Convert start and end to numpy arrays
    start = np.array(start, dtype=float)
    end = np.array(end, dtype=float)

    # Compute main direction vector and unit vector
    spring_vector = end-start
    total_length = np.linalg.norm(spring_vector)
    unit_dir = spring_vector/total_length  # Unit vector from start to end
    
    # Perpendicular vector
    perp_vector = np.array([-unit_dir[1], unit_dir[0], 0])

    # Setup stroke kwargs early
    stroke_kwargs = kwargs.copy()
    if "stroke_width" in stroke_kwargs:
        stroke_kwargs["width"] = stroke_kwargs.pop("stroke_width")

    spring = VGroup()

    # side bits
    g_star = 0.1 # length of side bits before spring starts
    def g(L):
        k = 5 / (2 * g_star)  
        return g_star * (np.exp(k * L) - 1) / (np.exp(k * L) + 1)

    gL = g(total_length)

    if type == 'zigzag':
        def sawtooth(x):
            return 2 * np.abs(np.mod(2 * x - 0.5, 2) - 1) - 1

        num_pts = 1000
        x = np.linspace(0, total_length, num_pts)

        # Step 1: define full sawtooth
        shifted_x = (x - gL) / (total_length - 2 * gL)
        y = coil_width * sawtooth(num_coils * shifted_x)

        # Step 2: zero ends where x < g(L) or x > L - g(L)
        y[x < gL] = 0
        y[x > total_length - gL] = 0

        # Step 3: rotate spring
        x_rot = x * unit_dir[0] - y * perp_vector[0]
        y_rot = x * unit_dir[1] - y * perp_vector[1]

        points = np.array([x_rot + start[0], y_rot + start[1], np.zeros(num_pts)]).T
        # spring = VMobject().set_points_as_corners(points).set_stroke(**stroke_kwargs)
        spring = VGroup(*[Line(points[i], points[i+1], **stroke_kwargs) for i in range(len(points)-1)])


    elif type == 'helical':
        stroke_kwargs = kwargs.copy()
        if "stroke_width" in stroke_kwargs:
            stroke_kwargs["width"] = stroke_kwargs.pop("stroke_width")

        num_pts = 1000  # Smooth helical shape
        coil_spacing = (total_length-2*coil_width)/num_coils
        alpha = np.pi*(2*num_coils+1)/(total_length-2*coil_width)

        # Generate helical spring points
        t = np.linspace(0, total_length-2*coil_width, num_pts)
        x = t+coil_width*np.cos(alpha*t-np.pi)+coil_width
        y = coil_width*np.sin(alpha*t-np.pi)

        # Rotate and shift
        x_rot = x*unit_dir[0]-y*perp_vector[0]
        y_rot = x*unit_dir[1]-y*perp_vector[1]

        points = np.array([x_rot+start[0], y_rot+start[1], np.zeros(num_pts)]).T
        helical_spring = VMobject().set_points_as_corners(points).set_stroke(**stroke_kwargs)
        
        spring.add(helical_spring)  
    return spring

############## SPRING AND DAMPER ###########

def springdamper(start=ORIGIN, end=UP * 3,
                num_coils=6, type="zigzag",
                width=0.5, fluid_color=BLUE,
                inline=True, **kwargs):
    """
    Combines a spring and a damper between two points.

    PARAMETERS
    ----------
    start : np.ndarray
        Start point of the combined element.
    end : np.ndarray
        End point of the combined element.
    num_coils : int
        Number of coils in the spring.
    type : str
        Spring type ("zigzag" or "helical").
    width : float
        Common width for both spring (2 * coil_width) and damper.
    fluid_color : Color
        Fill color of the damper's fluid.
    inline : bool
        If True, overlap spring and damper. If False, place them side by side.
    **kwargs : dict
        Additional stroke/fill options.

    RETURNS
    -------
    VGroup
        Combined spring and damper.
    """
    from manim import VGroup

    start = np.array(start, dtype=float)
    end = np.array(end, dtype=float)
    total_vec = end - start
    total_len = np.linalg.norm(total_vec)
    unit_dir = total_vec / total_len
    perp_dir = np.array([-unit_dir[1], unit_dir[0], 0])

    coil_width = 0.5 * width
    buffer = 0.2 * width  # spacing between spring and damper when side-by-side

    if inline:
        # Both at same position
        spring_mob = spring(start=start, end=end, num_coils=num_coils,
                        coil_width=coil_width, type=type, **kwargs)
        damper_mob = damper(start=start, end=end, width=width,
                        fluid_color=fluid_color, **kwargs)
    else:
        # Shift each component along perpendicular vector
        offset = (width + buffer) / 2
        spring_shift = -perp_dir * offset
        damper_shift = perp_dir * offset

        spring_mob = spring(start=start, end=end, num_coils=num_coils,
                        coil_width=coil_width, type=type, **kwargs)
        damper_mob = damper(start=start, end=end, width=width,
                        fluid_color=fluid_color, **kwargs)

        spring_mob.shift(spring_shift)
        damper_mob.shift(damper_shift)

    return VGroup(spring_mob, damper_mob)
    
def fixed_world(start=2*LEFT, end=2*RIGHT, spacing=None, mirror=False, line_or="right", diag_line_length=0.3, **kwargs):
    """
    Generates a fixed-world shape as a Manim VGroup between two points with diagonal support lines.

    PARAMETERS
    ----------
    start : np.ndarray 
        The start point of the fixed-world line.
    end : np.ndarray
        The end point of the fixed-world line.
    spacing : float | None, optional
        Distance between the diagonal support lines. If None, it is automatically calculated.
    mirror : bool, optional
        Whether to mirror the diagonal lines across the main line.
    diag_line_length : float, optional
        Length of the diagonal hatch lines.
    line_or : str, optional
        Direction of diagonal lines: "right" (default) or "left".
    color : Color
        Color of the main and diagonal lines.
    **kwargs : Any
        Additional keyword arguments passed to Manim's Line constructor (e.g., stroke_width, opacity).

    RETURNS
    -------
    VGroup
        A Manim VGroup containing the ceiling line and the diagonal support lines.
    """
    start = np.array(start, dtype=float)
    end = np.array(end, dtype=float)
    
    # Compute main direction vector and unit vector
    direction_vector = end - start
    total_length = np.linalg.norm(direction_vector)
    unit_dir = direction_vector / total_length if total_length != 0 else np.array([1, 0, 0])
    
    if spacing is None:
        if total_length <= 0.5:
            spacing = total_length  # Only start and end points for very short lines
        else:
            # Calculate number of segments needed (including both ends)
            num_segments = max(2, round(total_length / 0.5))
            spacing = total_length / (num_segments - 1)
        
    # Perpendicular vector for diagonal lines
    perp_vector = np.array([-unit_dir[1], unit_dir[0], 0])
    
    # Calculate diagonal direction
    if line_or == "right":
        diagonal_dir = (unit_dir + perp_vector) / np.linalg.norm(unit_dir + perp_vector)
    elif line_or == "left":
        diagonal_dir = -(unit_dir - perp_vector) / np.linalg.norm(unit_dir + perp_vector)
    
    # Normalize the diagonal direction
    diagonal_dir_norm = np.linalg.norm(diagonal_dir)
    if diagonal_dir_norm > 0:
        diagonal_dir = diagonal_dir / diagonal_dir_norm
    
    # Apply mirroring if needed (properly accounting for the original angle)
    if mirror ==True:
        # Calculate the reflection matrix for the main line direction
        u = unit_dir[0]
        v = unit_dir[1]
        reflection_matrix = np.array([
            [2*u**2-1, 2*u*v, 0],
            [2*u*v, 2*v**2-1, 0],
            [0, 0, 1]
        ])
        diagonal_dir = reflection_matrix @ diagonal_dir

    # Create the main line
    ceiling_line = Line(start=start, end=end, **kwargs)
    
    if total_length == 0:
        positions = [0]
    else:
        num_lines = max(2, int(round(total_length / spacing)) + 1)
        positions = np.linspace(0, total_length, num_lines)
    
    diagonal_lines = VGroup(*[
        Line(
            start=start + i * spacing * unit_dir,
            end=start + i * spacing * unit_dir + diag_line_length * diagonal_dir
        , **kwargs)
        for i in range(num_lines)
    ])

    return VGroup(ceiling_line, diagonal_lines)


# Mass functions
def rect_mass(pos= ORIGIN, width=1.5, height=1.5, font_size=None, label="m", label_color=WHITE, **kwargs):
    """
    Generates a mass object as a rectangle with centered text.

    PARAMETERS
    ----------
    pos : np.ndarray | Sequence[float]
        The position of the center of mass.
    width : float
        Width of the rectangular mass.
    height : float
        Height of the rectangular mass.
    font_size : float | None
        Font size of the mass label. If None, scaled proportionally to height.
    label : str
        Text displayed inside the mass.
    label_color : Color
        Color of the label.
    **kwargs : Any
        Additional arguments passed to the Rectangle constructor 
        (e.g., stroke_width, fill_color, fill_opacity).

    RETURNS
    -------
    VGroup
        A Manim VGroup containing the rectangular mass and its label.
    """
    # Validate inputs
    if height <= 0:
        warnings.warn("Height must be a positive value, Setting to default value (1.5).", UserWarning)
        height = 1.5
    if width <= 0:
        warnings.warn("Width must be a positive value, Setting to default value (1.5).", UserWarning)
        height = 1.5
    if font_size is None: #scale font according to size
        font_size=50*(height/1.5)
    elif font_size <= 0:
        warnings.warn("Font size must be a positive value, Setting to default value (50).", UserWarning)
        font_size = 50*(height/1.5)

    rect_mass = VGroup()
    label = MathTex(label, font_size=font_size, color = label_color)

    # Create shape
    shape = Rectangle(width=width, height=height, **kwargs)

    # Positioning
    shape.move_to(pos)
    label.move_to(pos)

    rect_mass.add(shape, label)
    return rect_mass

def circ_mass(pos= ORIGIN, radius=1.5, font_size=None, label="m", label_color=WHITE, **kwargs):
    """
    Generates a mass object as a circle with centered text.

    PARAMETERS
    ----------
    pos : np.ndarray | Sequence[float]
        The position of the center of mass.
    radius : float
        Radius of the circular mass.
    font_size : float | None
        Font size of the mass label. If None, scaled proportionally to radius.
    label : str
        Text displayed inside the mass.
    label_color : Color
        Color of the label
    **kwargs : Any
        Additional arguments passed to the Circle constructor 
        (e.g., stroke_width, fill_color, fill_opacity).

    RETURNS
    -------
    VGroup
        A Manim VGroup containing the circular mass and its label.
    """
    # Validate inputs
    if radius <= 0:
        warnings.warn("Size must be a positive value, Setting to default value (1.5).", UserWarning)
        radius = 1.5
    if font_size is None: #scale font according to size
        font_size=50*(radius/1.5)
    elif font_size <= 0:
        warnings.warn("Font size must be a positive value, Setting to default value (50).", UserWarning)
        font_size = 50*(radius/1.5)

    circ_mass = VGroup()
    label = MathTex(label, font_size=font_size, color=label_color)

    # Create shape
    shape = Circle(radius=radius/2, **kwargs)

    # Positioning
    shape.move_to(pos)
    label.move_to(pos)

    circ_mass.add(shape, label)
    return circ_mass

# Damper function
def damper(start=ORIGIN, end=UP*3, width=0.5, fluid_color=BLUE, **kwargs):
    """
    Generates a damper shape as a Manim VGroup between two points. 

    PARAMETERS
    ----------
    start : np.ndarray | Sequence[float]
        The start point of the damper.
    end : np.ndarray | Sequence[float]
        The end point of the damper.
    width : float
        Width of the damper box.
    fluid_color : ManimColor | None
        Color of the fluid. If None, defaults to a predefined color.
    **kwargs : Any
        Additional keyword arguments passed to Manim's Line constructor (e.g., stroke_width, opacity).

    RETURNS
    -------
    VGroup
        A Manim VGroup containing the damper box and damper rod.
    """
    start = np.array(start, dtype=float)
    end = np.array(end, dtype=float)

    damper_vector = end - start
    total_length = np.linalg.norm(damper_vector)
    unit_dir = damper_vector / total_length
    box_length=1.5
    def end_length_actual(L):
        k = 1 / 0.2
        return 0.2 * (np.exp(k * L) - 1) / (np.exp(k * L) + 1)                
    end_length_L = end_length_actual(total_length)

    def box_length_actual(L):
        k = 1.2 / box_length
        return box_length * (np.exp(k * L) - 1) / (np.exp(k * L) + 1)
    box_length_L = box_length_actual(total_length)

    # distance between piston and upper casing of damper
    def delta(L):
        k = 1
        c = 1.3
        return box_length_L * (1+np.exp(-k*c))/(1+np.exp(k*(L-c)))
    delta_L = delta(total_length)

    piston_length = total_length + delta_L - end_length_L - box_length_L

    perp_vector = np.array([-unit_dir[1], unit_dir[0], 0])

    # Rod
    damp_vertical_top = Line(end, end - unit_dir * (piston_length), **kwargs)
    damp_vertical_bottom = Line(start, start + unit_dir * end_length_L, **kwargs)
    damp_hor_top = Line(damp_vertical_top.get_end() - (perp_vector * (width / 2 - 0.02)),
                        damp_vertical_top.get_end() + (perp_vector * (width / 2 - 0.02)), **kwargs)

    # Box
    hor_damper = Line(damp_vertical_bottom.get_end() - (perp_vector * width / 2),
                        damp_vertical_bottom.get_end() + (perp_vector * width / 2), **kwargs)
    right_wall = Line(hor_damper.get_start(), hor_damper.get_start() + unit_dir * box_length_L, **kwargs)
    left_wall = Line(hor_damper.get_end(), hor_damper.get_end() + unit_dir * box_length_L, **kwargs)
    left_closing = Line(left_wall.get_end(), left_wall.get_end() - perp_vector * (width / 2 - 0.05), **kwargs)
    right_closing = Line(right_wall.get_end(), right_wall.get_end() + perp_vector * (width / 2 - 0.05), **kwargs)

    # Fluid
    fluid_corners = [
        hor_damper.get_start(),
        hor_damper.get_end(),
        left_wall.get_end(),
        right_wall.get_end(),
    ]
    fluid_fill = Polygon(*fluid_corners, fill_color=fluid_color, fill_opacity=0.4, stroke_width=0)

    damper_box = VGroup(hor_damper, left_wall, right_wall,
                        damp_vertical_bottom, left_closing, right_closing, fluid_fill)
    damper_rod = VGroup(damp_vertical_top, damp_hor_top)

    return VGroup(damper_box, damper_rod)   