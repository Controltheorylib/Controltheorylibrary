from manim import *
from controltheorylib import *

class PZMapExample(Scene):
    def construct(self):
        # Define transfer function G(s) = (s-1)/((s+2)(s+3))
        pzmap = PoleZeroMap("(s-1)/((s+2)*(s+3))")
        
        # Add title to the pole-zero map
        pzmap.title(r"G(s) = \frac{s-1}{(s+2)(s+3)}", use_math_tex=True)
        
        # Add to the scene
        self.add(pzmap)
