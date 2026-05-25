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

#Control loop system classes
__all__ = ['ControlSystem', 'ControlBlock', 'Connection']
class ControlBlock(VGroup):
    """
    A configurable block for control system diagrams.

    This class represents various types of blocks used in control system diagrams,
    including transfer function blocks, summing junctions, and input blocks.
    Each block can have multiple input and output ports with customizable properties.

    Parameters
    ----------
    name : str
        Unique identifier for the block. If empty, an automatic name is generated.
    block_type : str
        Type of block to create. Supported types:
        - "input": Input signal block
        - "transfer_function": Transfer function block (rectangular)
        - "summing_junction": Summing junction block (circular)
    position : np.ndarray or Sequence[float]
        Position coordinates for the block center.
    params : dict, optional
        Configuration parameters for the block. See Notes for details.
    """
    def __init__(self, name, block_type, position, params=None):
        super().__init__()
        self.name = name
        self.type = block_type
        self.position = position
        self.input_ports = {}
        self.output_ports = {}
        
        # Default parameters
        default_params = {
            "use_mathtex": False,
            "fill_opacity": 0.2,
            "label_scale": None,
            "font_size": None,
            "tex_template": None,
            "color": WHITE,
            "fill_color": None,
            "port_color": BLUE,
            "port_size": 0.005,
            "label_color": None,
            "block_width": 2.0,
            "block_height": 1.0,
            "summing_size": 0.6,
            "width_font_ratio": 0.3,
            "stroke_width": 0.5,
            "height_font_ratio": 0.5,
            "label": ""
        }
        
        # Type-specific defaults
        type_params = {}
        if block_type == "summing_junction":
            type_params.update({
                "input1_dir": LEFT,
                "input2_dir": DOWN,
                "output1_dir": RIGHT,
                "output2_dir": UP,
                "input1_sign": "+",
                
                "input2_sign": "+",
                "hide_labels": True,
                "width_font_ratio": 0.2, 
                "height_font_ratio": 0.2
            })

        if block_type == "transfer_function":
            type_params.update({
                "input_dirs": [LEFT],  # Default input direction
                "output_dirs": [RIGHT],  # Default output direction
                "input_names": ["in_left"],  # Default input port names
                "output_names": ["out_right"],  # Default output port names
                "extra_ports": False  # Whether to add secondary ports
            })

        if block_type == "gain":
            type_params.update({
                "block_width": 1.0,
                "block_height": 1.0,
            })
            
        self.params = default_params | type_params | (params or {})  # Merge with user params

        # Calculate automatic font sizes if not specified
        if block_type == "summing_junction":
            size = self.params["summing_size"]
            auto_font_size = size * 45  # Base scaling for circles
        else:
            width = self.params["block_width"]
            height = self.params["block_height"]
            auto_font_size = min(width * self.params["width_font_ratio"], 
                                height * self.params["height_font_ratio"]) * 75
            
        # Set font sizes if not explicitly provided
        if self.params["font_size"] is None:
            self.params["font_size"] = auto_font_size

        # Calculate label scale if not specified
        if self.params["label_scale"] is None:
            self.params["label_scale"] = auto_font_size / 90

        if self.params["label_color"] is None:
            self.params["label_color"] = self.params["color"]

        if self.params["use_mathtex"]:
            self.label = MathTex(
                self.params["label"],
                font_size=self.params["font_size"],
                tex_template=self.params["tex_template"],
                color=self.params["label_color"]
            )
        else:
            self.label = Text(
                self.params["label"],
                font_size=self.params["font_size"],
                color=self.params["label_color"]
            )
        self.label.scale(self.params["label_scale"])

        # Create background shape
        fill_color = self.params["fill_color"] if self.params["fill_color"] is not None else self.params["color"]
        
        if block_type == "summing_junction":
            self.background = Circle(
                radius=self.params["summing_size"]/2,
                fill_opacity=self.params["fill_opacity"], 
                fill_color=fill_color,
                color=self.params["color"],
                stroke_width=self.params["stroke_width"]
            )
        elif block_type == "gain":
            self.background = Triangle(
                fill_opacity=self.params["fill_opacity"],
                fill_color=fill_color,
                color=self.params["color"],
                stroke_width=self.params["stroke_width"]
            )
            self.background.rotate(-PI/2)
            self.background.stretch_to_fit_width(self.params["block_width"])
            self.background.stretch_to_fit_height(self.params["block_height"])
        else:
            self.background = Rectangle(
                width=self.params["block_width"],
                height=self.params["block_height"],
                fill_opacity=self.params["fill_opacity"],
                fill_color=fill_color,
                color=self.params["color"],
                stroke_width=self.params["stroke_width"]
            )
        
         # Create background and add components
        self.add(self.background, self.label)

        # Initialize block-specific components
        {
            "input": self._create_input,
            "transfer_function": self._create_transfer_function,
            "summing_junction": self._create_summing_junction,
            "gain": self._create_gain
        }[block_type]()
        
        self.move_to(position)

    def _create_input(self):
        self.add_port("out", RIGHT)

    def _create_gain(self):
        self.add_port("in", LEFT)
        self.add_port("out", RIGHT)

    def _create_transfer_function(self):
        """Create transfer function block with customizable ports"""
        # Handle inputs
        input_dirs = self.params.get("input_dirs", [LEFT])
        input_names = self.params.get("input_names", [f"in_{i}" for i in range(len(input_dirs))])
        
        for direction, name in zip(input_dirs, input_names):
            self.add_port(name, direction)
        
        # Handle outputs
        output_dirs = self.params.get("output_dirs", [RIGHT])
        output_names = self.params.get("output_names", [f"out_{i}" for i in range(len(output_dirs))])
        
        for direction, name in zip(output_dirs, output_names):
            self.add_port(name, direction)

    def _create_summing_junction(self):
        """Create summing junction with customizable ports"""
        # Input ports configuration
        input_dirs = [
            self.params.get("input1_dir", LEFT),
            self.params.get("input2_dir", DOWN)
        ]
        # Add any additional input directions if specified
        if "input3_dir" in self.params:
            input_dirs.append(self.params["input3_dir"])
        if "input4_dir" in self.params:
            input_dirs.append(self.params["input4_dir"])
        
        # Generate direction-based names
        direction_map = {
            tuple(LEFT): "left",
            tuple(RIGHT): "right",
            tuple(UP): "top",  # Changed from "up" to "top" to match your convention
            tuple(DOWN): "bottom"  # Changed from "down" to "bottom"
        }
        
        # Generate input port names
        input_names = self.params.get("input_names", [
            f"in_{direction_map.get(tuple(d), str(i))}" 
            for i, d in enumerate(input_dirs, 1)
        ])
        
        # Add input ports
        for direction, name in zip(input_dirs, input_names):
            self.add_port(name, direction)
        
        # Output ports configuration
        output_dirs = [
            self.params.get("output1_dir", RIGHT),
            self.params.get("output2_dir", UP)
        ]
        
        # Generate output port names
        output_names = self.params.get("output_names", [
            f"out_{direction_map.get(tuple(d), str(i))}" 
            for i, d in enumerate(output_dirs, 1)
        ])
        
        # Add output ports
        for direction, name in zip(output_dirs, output_names):
            self.add_port(name, direction)
        
        # Add signs if not hidden
        if not self.params.get("hide_labels", True):
            for i, name in enumerate(input_names, 1):
                sign_key = f"input{i}_sign"
                if sign_key in self.params:
                    tex = MathTex(self.params[sign_key]).scale(0.7)
                    direction = input_dirs[i-1]
                    tex.next_to(self.input_ports[name], -direction, buff=0.1)
                    self.add(tex)

    def add_port(self, name, direction):
        """Adds a port with size scaled to block type"""
        port = Dot(radius=self.params["port_size"], color=self.params["port_color"]).next_to(
            self.background,
            direction,
            buff=0
        )

        # Convert direction to tuple for comparison
        dir_tuple = tuple(direction)

        # Standard directions as tuples
        LEFT_TUPLE = tuple(LEFT)
        RIGHT_TUPLE = tuple(RIGHT)
        UP_TUPLE = tuple(UP)
        DOWN_TUPLE = tuple(DOWN)

        # For summing junctions, treat all ports explicitly
        if self.type == "summing_junction":
            if name.startswith("in"):
                self.input_ports[name] = port
            elif name.startswith("out"):
                self.output_ports[name] = port
            else:
                # Fallback logic using tuple comparison for summing junction if not explicitly named in/out
                if dir_tuple in [LEFT_TUPLE, DOWN_TUPLE]:
                    self.input_ports[name] = port
                else:
                    self.output_ports[name] = port
        else:
            # For non-summing blocks, prioritize explicit naming (e.g., "in_" or "out_")
            # If not explicitly named, then use direction-based convention
            if name.startswith("in_"):
                self.input_ports[name] = port
            elif name.startswith("out_"):
                self.output_ports[name] = port
            elif dir_tuple in [LEFT_TUPLE, DOWN_TUPLE]:
                self.input_ports[name] = port
            else:
                self.output_ports[name] = port

        self.add(port)
class Connection(VGroup):
    """
    A connection between two control blocks with optional labeling.
    
    Represents a signal flow connection between output and input ports of
    control blocks. Supports both LaTeX and regular text labels.
    
    Parameters
    ----------
    source_block : ControlBlock
        Source block where the connection originates
    output_port : str
        Name of the output port on the source block
    dest_block : ControlBlock
        Destination block where the connection terminates
    input_port : str
        Name of the input port on the destination block
    label : str, optional
        Text label to display along the connection
    label_font_size : float, optional
        Font size for the label (default: 35)
    color : Manim color, optional
        Color of the connection arrow (default: WHITE)
    use_math_tex : bool, optional
        Use LaTeX rendering for the label (default: True)
    buff : float, optional
        Buffer distance between label and arrow (default: 0.2)
    **kwargs
        Additional arguments passed to Arrow constructor
    """
    def __init__(self, source_block, output_port, dest_block, input_port, label=None,label_font_size=35,
                 color=WHITE, use_math_tex=True, buff=0.2, **kwargs):
        super().__init__()
        self.source_block = source_block
        self.dest_block = dest_block
        
        # Get port positions
        start = source_block.output_ports[output_port].get_center()
        end = dest_block.input_ports[input_port].get_center()
        
        # Create arrow
        self.arrow = Arrow(
            start, 
            end,
            stroke_width=3,
            tip_length=0.25,
            max_tip_length_to_length_ratio=0.5,
            buff=0.02,
            color=color,
            **kwargs
        )
        
        # Add label if provided
        if label and use_math_tex==True:
            self.label = MathTex(label, font_size=label_font_size,color=color)
            self.label.next_to(self.arrow.get_center(), UP, buff=buff)
            self.add(self.label)
        
        # Add regular label if mathtex bool is set to false
        if label and use_math_tex==False:
            self.label = Text(label, font_size=label_font_size,color=color)
            self.label.next_to(self.arrow.get_center(), UP, buff=buff)
            self.add(self.label)
        
        self.path = self.arrow
        self.add(self.arrow)

class ControlSystem:
    """
    A complete control system diagram manager.
    
    This class manages the creation, connection, and animation of control system
    components including blocks, connections, inputs, outputs, and feedback paths.
    """
    def __init__(self):
        self.blocks = OrderedDict()  
        self._block_counter = 0 

        self.connections = []
        self.disturbances = []
        
        
    def add_block(self, name, block_type, position, params=None):
        """Adds a new block to the system

        PARAMETERS
        ----------
        name : str
            Name of the block
        block_type : str
            Type of block, which can be of type:
              -summing_junction: Creates a summing junction (circular)
              -transfer_function: Creates a transfer function (rectangular)
        position : np.ndarray | Sequence[float]
            The position of the block
        params : any  
            Further parameter specifications of the block:
              -label; 
              use_math_tex, ...
        """
        if not name.strip():  # If name is empty
            name = f"{block_type}_{self._block_counter}"
            self._block_counter += 1

        new_block = ControlBlock(name, block_type, position, params)
        self.blocks[name] = new_block


        return new_block
        
    def connect(self, source_block, output_port, dest_block, input_port, style="default", label=None, font_size=30,
                use_math_tex=True, **kwargs):
        """Connect blocks with arrow and optional label
    
        PARAMETERS
        ----------
        source_block : ControlBlock | str
            The block the connection should start from
        output_port : str
            The port of the source_block where the connection should start from
        dest_block : ControlBlock | str
            The block the connection should go to
        input_port : str
            The port of the dest_block where the connection should go to
        style : str
            Style of the arrow which can be any of:
            -default: Continuous connection with standard settings
            -dashed: Dashed connection
            -bold: Continuous connection with increased stroke_width 
        label : str
            Label of the connection
        font_size : float
            Font size of the label
        use_math_tex : bool
            Boolean which determines whether the label should be rendered in LaTeX or regular text:
            -If true: LaTeX
            -If false: Regular text
        **kwargs : any 
            Additional arguments to be passed to the connection such as:
            Color: color of the connection
            stroke_width: Thickness of the line connection

        """
    # Input validation
        if output_port not in source_block.output_ports:
            raise ValueError(f"Source block '{source_block.name}' has no output port '{output_port}'")
        if input_port not in dest_block.input_ports:
            raise ValueError(f"Destination block '{dest_block.name}' has no input port '{input_port}'")
    
    # Create connection with arrow
        connection = Connection(
        source_block, 
        output_port, 
        dest_block, 
        input_port,
        label=label,
        label_font_size=font_size,
        use_math_tex=use_math_tex,
        **kwargs
        )
    
    # Apply style if specified
        if style == "dashed":
            connection.arrow.set_stroke(dash_length=0.15)
        elif style == "bold":
            connection.arrow.set_stroke(width=3.5)
    
        self.connections.append(connection)
        return connection

    def insert_between(self, new_block, source_block, dest_block):
        """Inserts a block between two existing blocks

        PARAMETERS
        ----------
        new_block : ControlBlock | str
            Add new block 
        source_block : ControlBlock | str
            The block where the connection originates from
        dest_block : ControlBlock | str
            The block where the connection goes to 
        """
        # Find and remove the old connection
        old_conn = self._find_connection(source_block, dest_block)
        if old_conn:
            self.connections.remove(old_conn)
            # Create new connections
            self.connect(source_block, old_conn.output_port, new_block, "in")
            self.connect(new_block, "out", dest_block, old_conn.input_port)
    
    def add_input(self, target_block, input_port, length=2, buff=0.05, label=None, use_math_tex=True, font_size=30, **kwargs):
        """Adds an input arrow to a block.
        
        PARAMETERS
        ----------

        target_block : ControlBlock | str
            The block where the input should be applied to
        input_port : str
            The input port where the input should go to from the selected target block
        length : float
            The length of the input connection
        buff : float
            The buffer between the end point of the arrow and the input port
        label : str
            Label of the input
        font_size : float
            Font size of the label
        use_math_tex : bool
            Boolean which determines whether the label should be rendered in LaTeX or regular text
        **kwargs : any
            Additional arguments to be passed to Arrow:
            -stroke_width: Thickness of the arrow line
            -stroke_opacity: Opacity of the arrow
            -color: color of the arrow
        """
        end = target_block.input_ports[input_port].get_center()

        source_input_port_direction = end - target_block.background.get_center()

        source_input_port_direction = source_input_port_direction / np.linalg.norm(source_input_port_direction)
    
        if np.dot(source_input_port_direction, RIGHT) > 0.9: # input port is on the right
            target_dir ="RIGHT"
        elif np.dot(source_input_port_direction, LEFT) > 0.9: 
            target_dir = "LEFT"
        elif np.dot(source_input_port_direction, UP) > 0.9:
            target_dir = "UP"
        elif np.dot(source_input_port_direction, DOWN) > 0.9:
            target_dir = "DOWN"

        if target_dir == "LEFT":
            start = end + LEFT * length
        elif target_dir == "UP":
            start = end + UP * length
        elif target_dir == "RIGHT":
            start = end + RIGHT * length
        elif target_dir == "DOWN":
            start = end + DOWN * length


        arrow = Arrow(
            start, end,
            tip_length=0.25,
            buff=buff,
            **kwargs)
    
        input_group = VGroup(arrow)
    
        if label and use_math_tex==True:
            label = MathTex(label, font_size=font_size)
            label.next_to(arrow, UP, buff=buff)
            input_group.add(label)
        
        if label and use_math_tex==False:
            label = Text(label, font_size=font_size)
            label.next_to(arrow, UP, buff=buff)
            input_group.add(label)
        
        self.inputs = getattr(self, 'inputs', []) + [input_group]
        return input_group
    
    def add_output(self, source_block, output_port, length=2, use_math_tex=True, label=None, font_size = 25, color=WHITE, rel_label_pos=UP,**kwargs):
        """Adds an output arrow from a block
        
        PARAMETERS
        ----------

        source_block : ControlBlock | str
            The block where the output should originate from
        output_port : str
            The output port where the output should start from
        length : float
            The length of the output connection
        buff : float
            The buffer between the end point of the arrow and the output port
        label : str
            Label of the output
        font_size : float
            Font size of the label
        use_math_tex : bool
            Boolean which determines whether the label should be rendered in LaTeX or regular text
        **kwargs : any
            Additional arguments to be passed to Arrow:
            -stroke_width: Thickness of the arrow line
            -stroke_opacity: Opacity of the arrow
            -color: color of the arrow

        """
        start = source_block.output_ports[output_port].get_center()
    
        # Determine on which side the output port is
        source_output_port_direction = start - source_block.background.get_center()

        source_output_port_direction = source_output_port_direction / np.linalg.norm(source_output_port_direction)
    
        if np.dot(source_output_port_direction, RIGHT) > 0.9: # input port is on the right
            source_dir ="RIGHT"
        elif np.dot(source_output_port_direction, LEFT) > 0.9: 
            source_dir = "LEFT"
        elif np.dot(source_output_port_direction, UP) > 0.9:
            target_dir = "UP"
        elif np.dot(source_output_port_direction, DOWN) > 0.9:
            source_dir = "DOWN"


        if source_dir == "LEFT":
            end = start + LEFT * length
        elif source_dir == "UP":
            end = start + UP * length
        elif source_dir == "RIGHT":
            end = start + RIGHT * length
        elif source_dir == "DOWN":
            end = start + DOWN * length
        
        arrow = Arrow(
            start, end,
            stroke_width=3,
            tip_length=0.25,
            buff=0.05,
            color=color,
            **kwargs
        )
    
        output = VGroup(arrow)
  
        if label:
            if use_math_tex == True:
                label = MathTex(label, font_size=font_size, color=color)
            else:
                label = Text(label, font_size=font_size, color=color)
            label.next_to(arrow, rel_label_pos, buff=0.2)
            output.add(label)
        
        self.outputs = getattr(self, 'outputs', []) + [output]
        return output
    
    def add_feedback_path(self, source_block, output_port, dest_block, input_port,
                          vertical_distance=1.5,  
                          horizontal_distance=None, rel_start_offset = None, rel_end_offset = None,
                          label=None, use_math_tex=True, color=WHITE, label_pos=UP, label_buff=0.2, **kwargs):
        
        """
        Adds a feedback path that adapts to the input port direction of the destination.

        PARAMETERS
        ----------
        source_block : ControlBlock | str
            The block the feedback path should start from
        output_port : str
            The output port of the source block where the feedback path should start from
        dest_block : ControlBlock | str
            The block the feedback path should go to
        input_port : str
            The input port of the destination block the feedback path should go to
        vertical_distance : float
            The vertical distance the feedback path should shift upwards or downwards
        Horizontal distance  : float
            The vertical distance the feedback path should shift upwards or downwards
        rel_start_offset : np.ndarray | None
            The start offset relative to the output port of the source block of the feedback path
        rel_end_offset : np.ndarray | None
            The end offset relative to the input port of the destination block of the feedback path
        label : str | None
            Label of the feedback path
        use_math_tex : bool
            When True, uses Mathtex for the label. If False, uses regular Text.
        label_pos : np.ndarray | None
            Position relative to the path where the label should be placed. Common values
            are UP, DOWN, LEFT, RIGHT or specific direction arrays.
        label_buff : float
            Buffer distance between the label and the feedback path.
        color : Manim color
            Color of the feedback path
        **kwargs : Any
            Additional arguments passed to the Line constructor 
            (e.g., stroke_width, stroke_opacity).

        RETURNS
        -------
        VGroup
            A VGroup containing a set of lines representing the feedback path
        """    
        start = source_block.output_ports[output_port].get_center()
        end = dest_block.input_ports[input_port].get_center()

        source_output_port_direction = source_block.output_ports[output_port].get_center() - source_block.background.get_center()

        source_output_port_direction = source_output_port_direction / np.linalg.norm(source_output_port_direction)

        dest_input_port_direction = dest_block.input_ports[input_port].get_center() - dest_block.background.get_center()
        dest_input_port_direction = dest_input_port_direction / np.linalg.norm(dest_input_port_direction)

        path_label_point = None

        if np.dot(source_output_port_direction, RIGHT) > 0.9: # Source port is on the right
            source_dir ="RIGHT"
        elif np.dot(source_output_port_direction, LEFT) > 0.9: 
            source_dir = "LEFT"
        elif np.dot(source_output_port_direction, UP) > 0.9:
            source_dir = "UP"
        elif np.dot(source_output_port_direction, DOWN) > 0.9:
            source_dir = "DOWN"


        if source_dir == "LEFT":
            start_out = start + rel_start_offset if rel_start_offset is not None else start
            end = end + rel_end_offset if rel_end_offset is not None else end

            if horizontal_distance is None:
                horizontal_distance = abs(start_out[0] - end[0])

            mid1 = start + horizontal_distance*LEFT
            segments = [
            Line(start_out, mid1, color=color, **kwargs),
            Arrow(mid1, end, tip_length=0.2, buff=0, color=color, **kwargs)]
        if source_dir == "RIGHT":
            start_out = start + rel_start_offset if rel_start_offset is not None else start
            end = end + rel_end_offset if rel_end_offset is not None else end
            
            if horizontal_distance is None:
                horizontal_distance=abs(start_out[0]-end[0])

            mid1 = start_out + vertical_distance*DOWN
            mid2 = mid1 + horizontal_distance*LEFT
            segments = [
            Line(start_out, mid1, color=color, **kwargs),
            Line(mid1, mid2, color=color, **kwargs),
            Arrow(mid2, end, tip_length=0.2, buff=0, color=color, **kwargs)]
        if source_dir == "DOWN":
            start_out = start + rel_start_offset if rel_start_offset is not None else start
            end = end + rel_end_offset if rel_end_offset is not None else end

            if horizontal_distance is None:
                horizontal_distance=abs(start_out[0]-end[0])

            mid1 = start_out + vertical_distance*DOWN
            mid2 = mid1 + horizontal_distance*LEFT
            segments = [
                Line(start_out,mid1, color=color, **kwargs),
                Line(mid1, mid2, color=color, **kwargs),
                Arrow(mid2, end, tip_length=0.2, buff=0, color=color, **kwargs)
            ]
        
        if source_dir == "UP":
            start_out = start + rel_start_offset if rel_start_offset is not None else start
            end = end + rel_end_offset if rel_end_offset is not None else end

            if horizontal_distance is None:
                horizontal_distance=abs(start_out[0]-end[0])

            mid1 = start_out + vertical_distance*UP
            mid2 = mid1 + horizontal_distance*LEFT
            segments = [
                Line(start_out,mid1, color=color, **kwargs),
                Line(mid1, mid2, color=color, **kwargs),
                Arrow(mid2, end, tip_length=0.2, buff=0, color=color, **kwargs)
            ]


        # Create complete path
        feedback_arrow = VGroup(*segments)
        feedback_arrow.set_stroke(color=color, width=3)

        # Add label if specified
        feedback = VGroup(feedback_arrow)
        if label and use_math_tex==True:
            feedback_label = MathTex(label, font_size=30)
            if path_label_point is not None:
                feedback_label.next_to(path_label_point, label_pos, buff=label_buff)
            else: # Fallback if for some reason path_label_point isn't set
                feedback_label.next_to(feedback_arrow.get_center(), label_pos, buff=label_buff)
            feedback.add(feedback_label)

        if label and use_math_tex==False:
            feedback_label = Text(label, font_size=30)
            if path_label_point is not None:
                feedback_label.next_to(path_label_point, label_pos, buff=label_buff)
            else: # Fallback if for some reason path_label_point isn't set
                feedback_label.next_to(feedback_arrow.get_center(), label_pos, buff=label_buff)
            feedback.add(feedback_label)

        # Store feedback path
        self.feedbacks = getattr(self, 'feedbacks', []) + [feedback]

        return feedback
    
    def add_feedforward_path(self, source_block, output_port, dest_block, input_port,
                            vertical_distance=None, horizontal_distance=None, label=None, use_math_tex=True,
                            label_buff=0.2, rel_start_offset = None, rel_end_offset=None, font_size=30,
                            color=WHITE, **kwargs):
        """
        Adds a feedforward path that adapts to the input port direction of the destination.

        PARAMETERS
        ----------
        source_block : ControlBlock | str
            The block the feedforward path should start from
        output_port : str
            The output port of the source block where the feedforward path should start from
        dest_block : ControlBlock | str
            The block the feedforward path should go to
        input_port : str
            The input port of the destination block the feedforward path should go to
        vertical_distance : float
            The vertical distance the feedforward path should shift upwards or downwards
        Horizontal distance  : float
            The horizontal distance the feedforward path should shift upwards or downwards
        rel_start_offset : np.ndarray | None
            The start offset relative to the output port of the source block of the feedforward path
        rel_end_offset : np.ndarray | None
            The end offset relative to the input port of the destination block of the feedforward path
        label : String
            Label of the feedforward path
        use_math_tex : bool
            When True, uses Mathtex for the label. If False, uses regular Text.
        label_pos : np.ndarray | None
            Relative label position
        label_buff : float
            Buffer between arrow/Line and label
        font_size : float
            font size of label
        color : Manim color
            Color of the feedback path
        **kwargs : Any
            Additional arguments passed to the Line constructor 
            (e.g., stroke_width, stroke_opacity).

        RETURNS
        -------
        VGroup
            A VGroup containing a set of lines representing the feedforward path
        """
        
            # Get connection points
        start = source_block.output_ports[output_port].get_center()
        end = dest_block.input_ports[input_port].get_center()
        
        # Get input direction by comparing port position to block center
        input_dir = None
        port_center = dest_block.input_ports[input_port].get_center()
        block_center = dest_block.background.get_center()
        
        # Calculate direction vector from block center to port
        direction_vector = port_center - block_center
        if start[1] > end[1]:
            if horizontal_distance is None:
                horizontal_distance = abs(start[0] - end[0])
                mid1 = start + horizontal_distance*RIGHT
                segments = [
                Line(start, mid1, color=color, **kwargs),
                Arrow(mid1, end, tip_length=0.2, buff=0, color=color, **kwargs)
            ]
        # Normalize and compare to standard directions
        if np.linalg.norm(direction_vector) > 0:
            direction_vector = direction_vector / np.linalg.norm(direction_vector)
            
            # Compare with threshold for each direction
            if np.dot(direction_vector, LEFT) > 0.9:
                input_dir = "LEFT"
            elif np.dot(direction_vector, RIGHT) > 0.9:
                input_dir = "RIGHT"
            elif np.dot(direction_vector, UP) > 0.9:
                input_dir = "UP"
            elif np.dot(direction_vector, DOWN) > 0.9:
                input_dir = "DOWN"
            
        # Default to relative positioning if not a summing junction or direction not found
        if input_dir is None:
            input_dir = "LEFT" if end[0] < start[0] else "RIGHT"  # Simple left/right fallback
        
        # Calculate path based on input direction
        if input_dir == "LEFT":
            start_out = start + rel_start_offset if rel_start_offset is not None else start
            end = end + rel_end_offset if rel_end_offset is not None else end
            vertical_distance = UP*abs(end[1]-start_out[1])
            mid1 = start+vertical_distance
            if horizontal_distance is None:
                horizontal_distance = abs(mid1[0] - end[0])
            segments = [
            
                Arrow(mid1, end, tip_length=0.2, buff=0, color=color, **kwargs), 
                Line(start_out, mid1, color=color, **kwargs)
            ]
            label_pos = mid1 + DOWN * 0.2
        elif input_dir == "UP":
            if start[1] < end[1]:
                start_out = start + rel_start_offset if rel_start_offset is not None else start
                end = end + rel_end_offset if rel_end_offset is not None else end

                mid1 = start_out + UP *end[1]
                if horizontal_distance is None:
                    horizontal_distance = abs(mid1[0] - end[0])
                mid2 = mid1 + RIGHT * horizontal_distance
                segments = [
                    Line(mid1, mid2, color=color, **kwargs),
                    Arrow(mid2, end, tip_length=0.2, buff=0, color=color, **kwargs),
                    Line(start_out, mid1, color=color, **kwargs)
                ]
                label_pos = mid2 + UP * 0.2
            if start[1] > end[1]:
                start_out = start + rel_start_offset if rel_start_offset is not None else start
                end = end + rel_end_offset if rel_end_offset is not None else end
                if horizontal_distance is None:
                    horizontal_distance = abs(mid1[0] - end[0])
                mid1 = start_out + RIGHT * horizontal_distance
                segments = [
                    Arrow(mid1, end, tip_length=0.2, buff=0, color=color, **kwargs),
                    Line(start_out, mid1, color=color, **kwargs)
                ]
                label_pos = mid1 + UP * 0.2

        elif start[1] < end[1]: 
            vertical_distance=1
            # Default to standard path for other directions
            start_out = start + rel_start_offset if rel_start_offset is not None else start
            end = end + rel_end_offset if rel_end_offset is not None else end
            mid1 = start_out + UP * vertical_distance
            if horizontal_distance is None:
                horizontal_distance = abs(mid1[0] - end[0])
            segments = [
                Arrow(mid1, end, tip_length=0.2, buff=0, color=color, **kwargs),
                Line(start_out, mid1, color=color, **kwargs)
            ]
            label_pos = mid1 + DOWN * 0.2
        
        # Create complete path
        feedforward_arrow = VGroup(*segments)
        feedforward_arrow.set_stroke(color=color, width=3)
        
        # Add label if specified
        feedforward = VGroup(feedforward_arrow)
        if label and use_math_tex==True:
            label = MathTex(label, font_size=font_size)
            label.move_to(label_pos, buff=label_buff)
            feedforward.add(label)

        if label and use_math_tex==False:
            label = Text(label, font_size=font_size)
            label.move_to(label_pos, buff=label_buff)
            feedforward.add(label)

        # Store feedforward path
        self.feedforwards = getattr(self, 'feedforwards', []) + [feedforward]
        return feedforward
    
    def get_all_components(self):
        """Function which returns all current components of the block diagram in one single VGroup"""
        self.all_components = VGroup()
        
        # Add non-summing-junction blocks first
        for block in self.blocks.values():
            self.all_components.add(block)
        
        # Add connections and disturbances
        for connection in self.connections:
            self.all_components.add(connection)
        for disturbance in self.disturbances:
            self.all_components.add(disturbance)
        
        
        # Add inputs, outputs and feedbacks if they exist
        for input_arrow in getattr(self, 'inputs', []):
            self.all_components.add(input_arrow)
        for output_arrow in getattr(self, 'outputs', []):
            self.all_components.add(output_arrow)
        for feedback in getattr(self, 'feedbacks', []):
            self.all_components.add(feedback)
        for feedforward in getattr(self, 'feedforwards', []):
            self.all_components.add(feedforward)
        
        return self.all_components
    
    def _find_connection(self, source_block, dest_block):
        """Helper method to find connection between two blocks"""
        for conn in self.connections:
            if (conn.source_block == source_block and 
            conn.dest_block == dest_block):
               return conn
        return None
    
    def animate_signals(self, scene, *blocks,
                    spawn_interval=0.5,
                    signal_speed=0.8,
                    duration=10.0,
                    color=YELLOW, feedback_color=YELLOW, feedforward_color=YELLOW,
                    radius=0.12,
                    include_input=True,
                    include_output=True,
                    include_feedback=True, include_feedforward=True, feedforward_delay=None,feedback_delay=None):
        """
        Animates real-time signal flow for a given block diagram.

        Creates moving dots that travel along connections, inputs, outputs, feedback,
        and feedforward paths to visualize signal propagation through the control system.

        PARAMETERS
        ----------
        scene : Scene
            The Manim scene object where the animation will be rendered.
        *blocks : ControlBlock or str
            Variable number of blocks defining the main signal path sequence.
            Blocks can be provided as ControlBlock objects or block names.
            The animation will follow the connection path between these blocks in order.
        spawn_interval : float, optional
            Time interval between spawning new signal dots, in seconds.
            Smaller values create more frequent signals. (default: 0.5)
        signal_speed : float, optional
            Speed of signal dots movement in units per second. (default: 0.8)
        duration : float, optional
            Total duration of the animation in seconds. (default: 10.0)
        color : Manim color, optional
            Color of the main signal path dots. (default: YELLOW)
        feedback_color : Manim color, optional
            Color of the feedback path signal dots. (default: YELLOW)
        feedforward_color : Manim color, optional
            Color of the feedforward path signal dots. (default: YELLOW)
        radius : float, optional
            Radius of the signal dots. (default: 0.12)
        include_input : bool, optional
            Whether to animate signals on system input arrows. (default: True)
        include_output : bool, optional
            Whether to animate signals on system output arrows. (default: True)
        include_feedback : bool, optional
            Whether to animate signals on feedback paths. (default: True)
        include_feedforward : bool, optional
            Whether to animate signals on feedforward paths. (default: True)
        feedforward_delay : float or None, optional
            Delay before starting feedforward signal animation, in seconds.
            If None, automatically calculated based on signal path geometry. (default: None)
        feedback_delay : float or None, optional
            Delay before starting feedback signal animation, in seconds.
            If None, automatically calculated based on signal path geometry. (default: None)
        **kwargs : Any
            Additional arguments passed to the Dot constructor for signal dots:
            - fill_opacity: float - Opacity of the signal dots
            - stroke_width: float - Border stroke width
            - stroke_color: Manim color - Border color

        RETURNS
        -------
        Scene
            An animation of real-time signal flow
        """
        self.feedback_color = feedback_color
        self.spawn_interval = spawn_interval
        self.signal_speed = signal_speed
        self.duration = duration
        self.color = color
        self.radius = radius

        fade_in_duration = 0.2
        fade_out_duration = 0.2
        

        # Prepare path groups
        main_paths = []      
        feedback_paths = []  
        feedforward_paths = []
        disturbance_paths = [] 

        if hasattr(self, 'disturbances'):
            for disturbance in self.disturbances:
                if hasattr(disturbance, "path"):
                    if isinstance(disturbance.path, (Line, Arrow)):
                        disturbance_paths.append(disturbance.path.copy())
                    elif isinstance(disturbance.path, VGroup):
                        for part in disturbance.path:
                            if isinstance(part, (Line, Arrow)):
                                disturbance_paths.append(part.copy())


        # Collect regular input/output paths
        if include_input and hasattr(self, 'inputs'):
            for input_path in self.inputs:
                if isinstance(input_path[0], Arrow):
                    main_paths.append(input_path[0].copy())

        for i in range(len(blocks) - 1):
            conn = self._find_connection(blocks[i], blocks[i + 1])
            if conn:
                main_paths.append(conn.path.copy())

        if include_output and hasattr(self, 'outputs'):
            for output_path in self.outputs:
                if isinstance(output_path[0], Arrow):
                    main_paths.append(output_path[0].copy())

        if include_feedback and hasattr(self, 'feedbacks'):
            for feedback_path in self.feedbacks:
                if isinstance(feedback_path[0], (VGroup, list)):
                    for segment in feedback_path[0]:
                        if isinstance(segment, Line):
                            feedback_paths.append(segment.copy())
        # Feedforward paths
        if include_feedforward and hasattr(self, 'feedforwards'):
            for ff in self.feedforwards:
                for segment in ff[0]:  # the feedforward_arrow part
                    if isinstance(segment, Line):
                        feedforward_paths.append(segment.copy())
        
        if feedback_delay is None and feedback_paths:
            main_length = sum(p.get_length() for p in main_paths if hasattr(p, 'get_length'))
            feedback_delay = (main_length-1)/signal_speed
        elif feedback_delay is None:
            feedback_delay = 0 
        else:
            feedback_delay = feedback_delay
        
        # Feedforward delay
        if feedforward_delay is None and feedforward_paths:
            ff_start = feedforward_paths[0].get_start()
            main_start = main_paths[0].get_start() if main_paths else ff_start
            dist = np.linalg.norm(ff_start - main_start-2)
            feedforward_delay = (dist) / signal_speed
        elif feedforward_delay is None:
            feedforward_delay = 0
        else:
            feedforward_delay = feedforward_delay

        def animate_path_stream(path_list, stream_color=None, stream_radius=None, start_delay=0):
            valid_paths = [p for p in path_list if hasattr(p, 'get_length') and p.get_length() > 0.1]
            if not valid_paths:
                return lambda dt: None, 0  # Return a dummy updater if nothing valid

            total_length = sum(p.get_length() for p in valid_paths)

            def get_point_at_distance(distance):
                current_length = 0
                for path in valid_paths:
                    length = path.get_length()
                    if distance <= current_length + length:
                        return path.point_from_proportion((distance - current_length) / length)
                    current_length += length
                return valid_paths[-1].get_end()

            travel_time = total_length / signal_speed
            total_run_time = duration + travel_time
            signals = []
            
            start_time = [0,0]  # Mutable wrapper for time tracking

            def updater(dt):
                start_time[0] += dt
                t = start_time[0]

                while updater.next_spawn_time <= t <= duration:
                    dot = Dot(color=stream_color, radius=stream_radius)
                    dot.set_opacity(0)
                    scene.add(dot)

                    my_start_time = updater.next_spawn_time

                    def make_updater(my_start_time):
                        def dot_updater(mob, _dt=0):
                            elapsed = start_time[0] - my_start_time
                            
                            # Calculate fade-in and fade-out progress
                            fade_in_progress = min(1, elapsed / fade_in_duration)
                            fade_out_progress = max(0, (travel_time - elapsed) / fade_out_duration)

                            # Set position and opacity
                            if elapsed < 0 or elapsed > travel_time:
                                mob.set_opacity(0)
                                return

                            progress = elapsed / travel_time
                            mob.move_to(get_point_at_distance(progress * total_length))

                            # Determine opacity based on fade progress
                            if elapsed < fade_in_duration:
                                mob.set_opacity(fade_in_progress)
                            elif elapsed > travel_time - fade_out_duration:
                                mob.set_opacity(fade_out_progress)
                            else:
                                mob.set_opacity(1)
                                
                        return dot_updater

                    dot.add_updater(make_updater(my_start_time))
                    signals.append(dot)

                    updater.next_spawn_time += spawn_interval
            updater.next_spawn_time = start_delay

            return updater, travel_time + self.duration
        
        # Animate main stream
        main_updater, main_runtime = animate_path_stream(main_paths, stream_color=color, stream_radius=radius)
        feedforward_updater, _ = animate_path_stream(feedforward_paths, stream_color=feedforward_color, stream_radius=radius, start_delay=feedforward_delay) if feedforward_paths else (None, 0)
        # Animate feedback stream
        if feedback_paths:
            feedback_updater, feedback_runtime = animate_path_stream(feedback_paths, stream_color=feedback_color, stream_radius=radius, start_delay=feedback_delay)
        else:
            feedback_updater, feedback_runtime = None, 0


        disturbance_updater, disturbance_runtime = (
        animate_path_stream(disturbance_paths, color=RED)
        if disturbance_paths else (None, 0))

        # Register updaters
        scene.add_updater(main_updater)
        if feedback_updater:
            scene.add_updater(feedback_updater)
        if disturbance_updater:
            scene.add_updater(disturbance_updater)
        if feedforward_updater:
            scene.add_updater(feedforward_updater)
        
        # Wait for both to finish
        scene.wait(duration)

        # Cleanup
        scene.remove_updater(main_updater)
        if feedback_updater:
            scene.remove_updater(feedback_updater)
        if disturbance_updater:
            scene.remove_updater(disturbance_updater)
        if feedforward_updater:
            scene.remove_updater(feedforward_updater)
