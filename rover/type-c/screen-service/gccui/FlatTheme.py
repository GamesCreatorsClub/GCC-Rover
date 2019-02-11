#
# Copyright 2019 Games Creators Club
#
# MIT License
#

from gccui.components import *


class RectangleDecoration(Component):
    def __init__(self, colour):
        super(RectangleDecoration, self).__init__(None)  # Call super constructor to store rectable
        self.colour = colour

    def draw(self, surface):
        pygame.draw.rect(surface, self.colour, self.rect)


class FlatThemeFactory(BaseUIFactory):
    def __init__(self, font=None, background_colour=pygame.color.THECOLORS['darkgray'], mouse_over_colour=pygame.color.THECOLORS['lightgray']):
        super(FlatThemeFactory, self).__init__()
        self.background_colour = background_colour
        self.mouse_over_colour = mouse_over_colour
        self.font = font if font is not None else pygame.font.SysFont('Arial', 30)

    def setMouseOverColour(self, mouse_over_colour):
        self.mouse_over_colour = mouse_over_colour

    def setBackgroundColour(self, background_colour):
        self.background_colour = background_colour

    def label(self, rect, text, font=None, colour=None, h_alignment=ALIGNMENT.LEFT, v_alignment=ALIGNMENT.TOP):
        label = Label(rect, text, colour=colour, h_alignment=h_alignment, v_alignment=v_alignment)
        label.font = self.font
        return label

    def image(self, rect, image, h_alignment=ALIGNMENT.LEFT, v_alignment=ALIGNMENT.TOP):
        return Image(rect, image, h_alignment=h_alignment, v_alignment=v_alignment)

    def button(self, rect, onClick=None, onHover=None, label=None):
        return Button(rect, onClick, onHover, label,
                      background_decoration=RectangleDecoration(self.background_colour),
                      mouse_over_decoration=RectangleDecoration(self.mouse_over_colour))
