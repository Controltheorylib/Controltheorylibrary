from manim import *
from controltheorylib import *
import sympy as sp

class control_diagram_v1(Scene):
    def construct(self):
        # Configure background color to match the theme
        config.background_color = "#3d3d3d"
        
        # 1. Main Title
        title = Text("Feedback Control System with Feedforward Compensator", font_size=20)
        title.to_edge(UP, buff=0.4)
        self.add(title)
        
        # Initiate controlsystem 
        cs = ControlSystem()
        
        # 2. Create Blocks
        # Reference setpoint block (represented as a small block labeled r(s))
        setpoint = cs.add_block(
            "setpoint", "transfer_function", 4.5 * LEFT,
            params={
                "label": "r(s)",
                "use_mathtex": True,
                "block_width": 0.8,
                "block_height": 0.6,
                "output_dirs": [RIGHT, UP],
                "output_names": ["out_r", "out_up"],
                "color": WHITE
            }
        )
        
        # Summing Junction 1 (Error calculation: Reference - Feedback)
        sum1 = cs.add_block(
            "sum1", "summing_junction", 2.5 * LEFT,
            params={
                "input1_dir": LEFT,
                "input2_dir": DOWN,
                "input1_sign": "+",
                "input2_sign": "-",
                "hide_labels": False,
                "color": WHITE
            }
        )
        sum1.scale(0.7)
        
        # Feedback Controller C_fb(s)
        C_fb = cs.add_block(
            "C_fb", "transfer_function", 0.5 * LEFT,
            params={
                "label": "C_{fb}(s)",
                "use_mathtex": True,
                "color": ORANGE,
                "fill_color": DARK_GRAY,
                "fill_opacity": 0.4
            }
        )
        
        # Summing Junction 2 (Control combination: Feedback Controller + Feedforward Controller)
        sum2 = cs.add_block(
            "sum2", "summing_junction", 1.5 * RIGHT,
            params={
                "input1_dir": LEFT,
                "input2_dir": UP,
                "input1_sign": "+",
                "input2_sign": "+",
                "hide_labels": False,
                "color": WHITE
            }
        )
        sum2.scale(0.7)
        
        # Plant P(s)
        Plant = cs.add_block(
            "Plant", "transfer_function", 3.5 * RIGHT,
            params={
                "label": "P(s)",
                "use_mathtex": True,
                "color": GREEN,
                "fill_color": DARK_GRAY,
                "fill_opacity": 0.4
            }
        )
        
        # Feedforward Controller C_ff(s)
        C_ff = cs.add_block(
            "C_ff", "transfer_function", 0.5 * LEFT + 1.5 * UP,
            params={
                "label": "C_{ff}(s)",
                "use_mathtex": True,
                "color": YELLOW,
                "fill_color": DARK_GRAY,
                "fill_opacity": 0.4
            }
        )
        
        # 3. Add Connections
        r1_con = cs.connect(setpoint, "out_r", sum1, "in_left")
        e1_con = cs.connect(sum1, "out_right", C_fb, "in_left", label="e(s)")
        u1_con = cs.connect(C_fb, "out_right", sum2, "in_left")
        u2_con = cs.connect(sum2, "out_right", Plant, "in_left")
        
        # Plant output y(s)
        y_con = cs.add_output(Plant, "out_right", length=1.5, label="y(s)")
        
        # Feedback loop path (from Plant output back to Summing Junction 1 bottom input)
        feedback = cs.add_feedback_path(Plant, "out_right", sum1, "in_bottom", rel_start_offset=0.5 * RIGHT)
        
        # Feedforward paths
        # Reference branch going up and right into C_ff(s)
        feedforward_in = cs.add_feedforward_path(setpoint, "out_up", C_ff, "in_left")
        # C_ff(s) output going right and down into Summing Junction 2 top input
        feedforward_out = cs.add_feedforward_path(C_ff, "out_right", sum2, "in_top")
        
        # 4. Play Animations
        # Fade in the feedback loop first
        self.play(
            FadeIn(setpoint),
            FadeIn(sum1),
            FadeIn(r1_con),
            run_time=1
        )
        self.play(
            FadeIn(e1_con),
            FadeIn(C_fb),
            run_time=1
        )
        self.play(
            FadeIn(u1_con),
            FadeIn(sum2),
            run_time=1
        )
        self.play(
            FadeIn(u2_con),
            FadeIn(Plant),
            FadeIn(y_con),
            run_time=1
        )
        self.play(
            FadeIn(feedback),
            run_time=1
        )
        self.wait(1.0)
        
        # Fade in the feedforward path
        self.play(
            FadeIn(feedforward_in),
            FadeIn(C_ff),
            run_time=1
        )
        self.play(
            FadeIn(feedforward_out),
            run_time=1
        )
        self.wait(2.0)
