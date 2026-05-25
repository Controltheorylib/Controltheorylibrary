from manim import *
from controltheorylib import *
import numpy as np

class ImpulseResponseAnimation(Scene):
    def construct(self):
        # Configure background color to match the library theme
        config.background_color = "#3d3d3d"
        
        # 1. Main Title
        main_title = Text("Effect of Stiffness (k) on Pole Locations & Impulse Response", font_size=24)
        main_title.to_edge(UP, buff=0.4)
        self.add(main_title)
        
        # Scale factor for split screen layout
        scale_factor = 0.65
        shift_val = 2.8

        # 2. Left Side: Pole-Zero Map (initialized with k=10)
        # G(s) = 1 / (s^2 + s + 10)
        # We turn off dashed axis lines to follow the new styling preference
        pzmap = PoleZeroMap("1/(s**2+s+10)", x_range=[-4, 1, 1], y_range=[-6, 6, 2], dashed_axis=False)
        pzmap.scale(scale_factor)
        pzmap.shift(shift_val * LEFT + 0.5 * DOWN)
        
        # Title for the PZ Map side
        pz_title = MathTex(r"G(s) = \frac{1}{s^2 + s + k}", font_size=26)
        pz_title.next_to(pzmap.box, UP, buff=0.3)
        
        # 3. Right Side: Impulse Response Axes
        axes = Axes(
            x_range=[0, 10, 2],
            y_range=[-0.4, 0.4, 0.2],
            x_length=6,
            y_length=4.5,
            axis_config={"include_numbers": True, "stroke_width": 1}
        )
        axes.scale(scale_factor)
        axes.shift(3.2 * RIGHT + 0.5 * DOWN)
        
        # Labels for the time-domain graph
        axes_labels = axes.get_axis_labels(
            x_label=MathTex("t", font_size=22),
            y_label=MathTex("g(t)", font_size=22)
        )
        
        # Title for the impulse response side
        ir_title = Text("Impulse Response g(t)", font_size=20)
        ir_title.next_to(axes, UP, buff=0.4)
        
        # 4. Define Value Tracker for Dynamic Updates
        k_tracker = ValueTracker(10.0)
        
        # Analytical formula for the impulse response of G(s) = 1 / (ms^2 + cs + k)
        # with m=1, c=1, and dynamic k
        def impulse_response_val(t, k_val):
            m, c = 1.0, 1.0
            alpha = c / (2.0 * m)
            omega_d_sq = k_val / m - alpha**2
            if omega_d_sq <= 0:
                # Overdamped/critically damped case (fallback)
                omega_d = np.sqrt(abs(omega_d_sq))
                return (1.0 / (m * omega_d)) * np.exp(-alpha * t) * np.sinh(omega_d * t)
            else:
                omega_d = np.sqrt(omega_d_sq)
                return (1.0 / (m * omega_d)) * np.exp(-alpha * t) * np.sin(omega_d * t)

        # Dynamic curve redraws automatically as k_tracker value changes
        curve = always_redraw(lambda: axes.plot(
            lambda t: impulse_response_val(t, k_tracker.get_value()),
            x_range=[0, 10],
            color=YELLOW,
            stroke_width=3
        ))
        
        # Dynamic poles (X markers) on the complex plane redraw as k_tracker changes
        # Pole locations for s^2 + s + k = 0 are at s = -0.5 +/- i * sqrt(k - 0.25)
        # Note: scale_factor and stroke_width are scaled in proportion to the pzmap scale
        poles = always_redraw(lambda: VGroup(
            Cross(scale_factor=pzmap.markers_size * scale_factor, color=RED, stroke_width=12 * scale_factor).move_to(
                pzmap.axis.n2p(complex(-0.5, np.sqrt(k_tracker.get_value() - 0.25)))
            ),
            Cross(scale_factor=pzmap.markers_size * scale_factor, color=RED, stroke_width=12 * scale_factor).move_to(
                pzmap.axis.n2p(complex(-0.5, -np.sqrt(k_tracker.get_value() - 0.25)))
            )
        ))
        
        # Dynamic label showing the current value of k
        k_label = always_redraw(lambda: MathTex(
            rf"k = {k_tracker.get_value():.1f}",
            font_size=28,
            color=YELLOW
        ).next_to(ir_title, RIGHT, buff=0.4))
        
        # 5. Play Initial Assembly Animations
        # (We play pzmap.basecomponents to fade in the grid without the initial poles)
        self.play(
            FadeIn(pzmap.basecomponents),
            FadeIn(pz_title),
            Create(axes),
            Write(axes_labels),
            FadeIn(ir_title)
        )
        
        # Fade in the dynamic curve, dynamic poles, and current k value
        self.play(
            Create(curve),
            Create(poles),
            FadeIn(k_label),
            run_time=1.5
        )
        self.wait(1.5)
        
        # 6. Animate k moving from 10 to 20 over 6 seconds
        self.play(
            k_tracker.animate.set_value(20.0),
            run_time=6,
            rate_func=linear
        )
        self.wait(2.5)
