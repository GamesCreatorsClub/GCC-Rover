#
# Copyright 2019 Games Creators Club
#
# MIT License
#

from gccui.components import *


class ButtonDecoration(Component):
    def __init__(self, colour):
        super(ButtonDecoration, self).__init__(None)  # Call super constructor to store rectable
        self.colour = colour

    def draw(self, surface):
        pygame.draw.rect(surface, self.colour, self.rect)


class BorderDecoration(Component):
    def __init__(self, colour):
        super(BorderDecoration, self).__init__(None)  # Call super constructor to store rectable
        self.colour = colour

    def draw(self, surface):
        pygame.draw.rect(surface, self.colour, self.rect, 1)


class FlatThemeFactory(BaseUIFactory):
    def __init__(self, uiAdapter, font=None, colour=pygame.color.THECOLORS['cyan'], background_colour=pygame.color.THECOLORS['gray32'], mouse_over_colour=pygame.color.THECOLORS['lightgray']):
        super(FlatThemeFactory, self).__init__(uiAdapter)
        self.colour = colour
        self.background_colour = background_colour
        self.mouse_over_colour = mouse_over_colour
        self.font = font if font is not None else pygame.font.SysFont('Arial', 30)

    def setMouseOverColour(self, mouse_over_colour):
        self.mouse_over_colour = mouse_over_colour

    def setBackgroundColour(self, background_colour):
        self.background_colour = background_colour

    def label(self, rect, text, font=None, colour=None, h_alignment=ALIGNMENT.LEFT, v_alignment=ALIGNMENT.TOP, hint=UI_HINT.NORMAL):
        label = Label(rect, text, font=font if font is not None else self.font, colour=colour, h_alignment=h_alignment, v_alignment=v_alignment)
        return label

    def image(self, rect, image, h_alignment=ALIGNMENT.LEFT, v_alignment=ALIGNMENT.TOP, hint=UI_HINT.NORMAL):
        return Image(rect, image, h_alignment=h_alignment, v_alignment=v_alignment)

    def button(self, rect, onClick=None, onHover=None, label=None, hint=UI_HINT.NORMAL):
        background_colour = self.background_colour
        mouse_over_colour = self.mouse_over_colour
        if hint == UI_HINT.WARNING:
            background_colour = pygame.color.THECOLORS['darkorange3']
            mouse_over_colour = pygame.color.THECOLORS['darkorange']
        elif hint == UI_HINT.ERROR:
            background_colour = pygame.color.THECOLORS['indianred4']
            mouse_over_colour = pygame.color.THECOLORS['indianred']

        return Button(rect, onClick, onHover, label,
                      background_decoration=ButtonDecoration(background_colour),
                      mouse_over_decoration=ButtonDecoration(mouse_over_colour))

    def panel(self, rect, background_colour=None, hint=UI_HINT.NORMAL):
        if background_colour is None:
            if hint == UI_HINT.WARNING:
                background_colour = pygame.color.THECOLORS['orange']
            elif hint == UI_HINT.ERROR:
                background_colour = pygame.color.THECOLORS['red']
        return Panel(rect, background_colour, decoration=BorderDecoration(self.colour))

    def menu(self, rect, background_colour=None, hint=UI_HINT.NORMAL):
        if background_colour is None:
            if hint == UI_HINT.WARNING:
                background_colour = pygame.color.THECOLORS['orange']
            elif hint == UI_HINT.ERROR:
                background_colour = pygame.color.THECOLORS['red']
        return Menu(rect, self, background_colour, decoration=BorderDecoration(self.colour))
