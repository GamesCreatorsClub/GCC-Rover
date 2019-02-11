#
# Copyright 2019 Games Creators Club
#
# MIT License
#

from gccui.components import *


class RectangleDecoration(Component):
    def __init__(self, colour, background_colour):
        super(RectangleDecoration, self).__init__(None)  # Call super constructor to store rectable
        self.colour = colour
        self.background_colour = background_colour
        self.strip_width = 5
        self.strip_margin = 3
        self.cut_width = 6
        self.cut_margin = 3
        self.cut_size = 15

    def draw(self, surface):
        pygame.draw.rect(surface, self.background_colour, self.rect)

        x1 = self.rect.x
        x2 = self.rect.right - 1
        y1 = self.rect.y
        y2 = self.rect.bottom - 1
        pygame.draw.rect(surface, self.colour, pygame.Rect(x1, y1, self.strip_width, self.rect.height))
        pygame.draw.line(surface, self.colour, (x1 + self.strip_width + self.strip_margin, y1), (x2 - self.cut_size, y1))
        pygame.draw.line(surface, self.colour, (x2 - self.cut_size, y1), (x2, y1 + self.cut_size))
        pygame.draw.line(surface, self.colour, (x2, y1 + self.cut_size), (x2, y2))
        pygame.draw.line(surface, self.colour, (x2, y2), (x1 + self.strip_margin, y2))
        pygame.draw.line(surface, self.colour, (x1 + self.strip_width + self.strip_margin, y2), (x1 + self.strip_width + self.strip_margin, y1))

        pygame.draw.polygon(surface, self.colour, [
            (x2 - self.cut_size + self.cut_margin, y1),
            (x2 - self.cut_size + self.cut_margin + self.cut_width, y1),
            (x2, y1 + self.cut_size - self.cut_margin - self.cut_width),
            (x2, y1 + self.cut_size - self.cut_margin)
        ])


class BoxBlueSFThemeFactory(BaseUIFactory):
    def __init__(self, font=None,
                 colour=pygame.color.THECOLORS['cornflowerblue'],
                 background_colour=(0, 0, 0, 255),
                 mouse_over_colour=pygame.color.THECOLORS['yellow'],
                 mouse_over_background_colour=pygame.color.THECOLORS['gray32']):
        super(BoxBlueSFThemeFactory, self).__init__()
        self.colour = colour
        self.background_colour = background_colour
        self.mouse_over_colour = mouse_over_colour
        self.mouse_over_background_colour = mouse_over_background_colour
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
        colour = self.colour
        background_colour = self.background_colour
        mouse_over_colour = self.mouse_over_colour
        mouse_over_background_colour = self.mouse_over_background_colour
        if hint == UI_HINT.WARNING:
            colour = pygame.color.THECOLORS['orange']
            background_colour = self.background_colour
            mouse_over_colour = pygame.color.THECOLORS['orange']
            mouse_over_background_colour = pygame.color.THECOLORS['darkorange4']
        elif hint == UI_HINT.ERROR:
            colour = pygame.color.THECOLORS['red']
            background_colour = self.background_colour
            mouse_over_colour = pygame.color.THECOLORS['red']
            mouse_over_background_colour = pygame.color.THECOLORS['darkred']

        return Button(rect, onClick, onHover, label,
                      background_decoration=RectangleDecoration(colour, background_colour),
                      mouse_over_decoration=RectangleDecoration(mouse_over_colour, mouse_over_background_colour))
