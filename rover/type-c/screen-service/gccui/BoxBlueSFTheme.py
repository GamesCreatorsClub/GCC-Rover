#
# Copyright 2019 Games Creators Club
#
# MIT License
#

from gccui.components import *


class MenuButtonBackgroundDecoration(Component):
    def __init__(self, colour):
        super(MenuButtonBackgroundDecoration, self).__init__(None)  # Call super constructor to store rectable
        self.colour = colour

    def draw(self, surface):
        pygame.draw.rect(surface, self.colour, self.rect)


class ButtonRectangleDecoration(Component):
    def __init__(self, colour, background_colour):
        super(ButtonRectangleDecoration, self).__init__(None)  # Call super constructor to store rectable
        self.colour = colour
        self.background_colour = background_colour
        self.strip_width = 5
        self.strip_margin = 3
        self.cut_width = 6
        self.cut_margin = 3
        self.cut_size = 15

    def draw(self, surface):
        if self.background_colour is not None:
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


class BorderDecoration(Component):
    def __init__(self, rect, colour):
        super(BorderDecoration, self).__init__(rect)  # Call super constructor to store rectable
        self.colour = colour
        self.top_left_cut = 8
        self.bottom_right_cut = 5

    def draw(self, surface):
        x1 = self.rect.x
        x2 = self.rect.right - 1
        y1 = self.rect.y
        y2 = self.rect.bottom - 1

        pygame.draw.polygon(surface, self.colour, [
            (x1 + self.top_left_cut, y1),
            (x2, y1),
            (x2, y2 - self.bottom_right_cut),
            (x2 - self.bottom_right_cut, y2),
            (x1, y2),
            (x1, y1 + self.top_left_cut)
        ], 1)


class BoxBlueSFThemeFactory(BaseUIFactory):
    def __init__(self, uiAdapter,
                 font=None,
                 colour=pygame.color.THECOLORS['cornflowerblue'],
                 background_colour=(0, 0, 0, 255),
                 mouse_over_colour=pygame.color.THECOLORS['yellow'],
                 mouse_over_background_colour=pygame.color.THECOLORS['gray32']):
        super(BoxBlueSFThemeFactory, self).__init__(uiAdapter)
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
                      background_decoration=ButtonRectangleDecoration(colour, background_colour),
                      mouse_over_decoration=ButtonRectangleDecoration(mouse_over_colour, mouse_over_background_colour))

    def panel(self, rect, background_colour=None, hint=UI_HINT.NORMAL):
        if background_colour is None:
            if hint == UI_HINT.WARNING:
                background_colour = pygame.color.THECOLORS['orange']
            elif hint == UI_HINT.ERROR:
                background_colour = pygame.color.THECOLORS['red']
        return Panel(rect, background_colour, decoration=BorderDecoration(rect, self.colour))

    def menu(self, rect, background_colour=None, hint=UI_HINT.NORMAL):
        if background_colour is None:
            if hint == UI_HINT.WARNING:
                background_colour = pygame.color.THECOLORS['orange']
            elif hint == UI_HINT.ERROR:
                background_colour = pygame.color.THECOLORS['red']
        return Menu(rect, self, background_colour, decoration=BorderDecoration(rect, self.colour))

    def _menuItemTextButton(self, rect, label, callback):
        return self._menuItemButton(rect, self.label(None, label, h_alignment=ALIGNMENT.CENTER, v_alignment=ALIGNMENT.MIDDLE), callback)

    def _menuItemButton(self, rect, label, callback):
        return Button(rect, callback, label=label, mouse_over_decoration=MenuButtonBackgroundDecoration(self.mouse_over_background_colour))

    def border(self, rect, colour=pygame.color.THECOLORS['white']):
        return BorderDecoration(rect, colour)