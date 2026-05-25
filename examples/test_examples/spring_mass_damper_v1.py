from manim import *
from controltheorylib import *
import numpy as np

class SpringMassDamper_v1(Scene):
    def construct(self):
        # Background color
        config.background_color = "#3d3d3d"
        
        # 1. Main Title
        main_title = Text("Free Response of a Vertical Spring-Mass-Damper System", font_size=22)
        main_title.to_edge(UP, buff=0.4)
        self.add(main_title)
        
        # Parameters
        m, c, k = 1.0, 0.8, 12.0
        y0 = 1.2  # Initial displacement (upwards)
        
        # Free response calculation: y(t) = y0 * e^(-alpha * t) * (cos(wd * t) + (alpha/wd)*sin(wd * t))
        alpha = c / (2.0 * m)
        omega_d = np.sqrt(k/m - alpha**2)
        
        def free_response(t):
            return y0 * np.exp(-alpha * t) * (np.cos(omega_d * t) + (alpha / omega_d) * np.sin(omega_d * t))
            
        # 2. Time Tracker
        t_tracker = ValueTracker(0.0)
        
        # 3. Left Side: Mechanical System elements
        # Ceiling (Fixed World)
        ceiling = fixed_world(start=[-4.0, 2.5, 0], end=[-2.0, 2.5, 0], spacing=0.3, mirror=False)
        
        # Dynamic Spring-Damper in parallel (inline=False) using helical spring
        sd_system = always_redraw(lambda: springdamper(
            start=[-3.0, 2.5, 0],
            end=[-3.0, -0.5 + free_response(t_tracker.get_value()), 0],
            num_coils=8,
            type="helical",
            width=0.6,
            inline=False,
            fluid_color=BLUE,
            stroke_width=2
        ))
        
        # Dynamic mass block hanging at the bottom
        mass_block = always_redraw(lambda: rect_mass(
            pos=[-3.0, -1.0 + free_response(t_tracker.get_value()), 0],
            width=1.5,
            height=1.0,
            label="m",
            fill_color=DARK_GRAY,
            fill_opacity=0.8,
            stroke_width=2
        ))
        
        # 4. Right Side: Time Domain Plot
        axes = Axes(
            x_range=[0, 10, 2],
            y_range=[-1.5, 1.5, 0.5],
            x_length=6,
            y_length=4.5,
            axis_config={"include_numbers": True, "stroke_width": 1}
        )
        axes.scale(0.65)
        axes.shift(2.8 * RIGHT + 0.5 * DOWN)
        
        # Plot labels
        axes_labels = axes.get_axis_labels(
            x_label=MathTex("t", font_size=22),
            y_label=MathTex("y(t)", font_size=22)
        )
        
        # Plot Title
        plot_title = Text("Displacement y(t) vs t", font_size=18)
        plot_title.next_to(axes, UP, buff=0.4)
        
        # Dynamic curve drawn up to current time
        response_curve = always_redraw(lambda: axes.plot(
            lambda t: free_response(t),
            x_range=[0, max(0.001, t_tracker.get_value())],
            color=YELLOW,
            stroke_width=3
        ))
        
        # Dynamic tracking dot on the curve
        tracking_dot = always_redraw(lambda: Dot(color=RED).move_to(
            axes.c2p(t_tracker.get_value(), free_response(t_tracker.get_value()))
        ))
        
        # 5. Play Assembly and Simulation
        self.play(
            Create(ceiling),
            Create(axes),
            Write(axes_labels),
            FadeIn(plot_title)
        )
        
        self.play(
            Create(sd_system),
            Create(mass_block),
            Create(response_curve),
            Create(tracking_dot),
            run_time=1.5
        )
        self.wait(1.0)
        
        # Run free response simulation over 10 seconds
        self.play(
            t_tracker.animate.set_value(10.0),
            run_time=10,
            rate_func=linear
        )
        self.wait(2.0)
