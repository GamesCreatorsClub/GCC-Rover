
#
# Copyright 2019 Games Creators Club
#
# MIT License
#

import pygame


class ALIGNMENT:
    LEFT = 1
    CENTER = 2
    RIGHT = 3
    TOP = 4
    MIDDLE = 5
    BOTTON = 6


class Component:
    def __init__(self, rect):
        self.rect = rect
        self.mouse_is_over = False
        self.font = None
        self._visible = True

    def _font(self):
        if self.font is None:
            self.font = pygame.font.SysFont('Arial', 30)
        return self.font

    def isVisible(self):
        return self._visible

    def setVisible(self, visible):
        self._visible = visible

    def draw(self, surface):
        pass

    def redefineRect(self, rect):
        self.rect = rect

    def mouseOver(self, mousePos):
        self.mouse_is_over = True

    def mouseLeft(self, mousePos):
        self.mouse_is_over = False

    def mouseDown(self, mousePos):
        pass

    def mouseUp(self, mousePos):
        pass


class Collection(Component):
    def __init__(self, rect):
        super(Collection, self).__init__(rect)  # Call super constructor to store rectable
        self.components = []
        self._selectedComponent = None

    def addComponent(self, component):
        self.components.append(component)

    def removeComponent(self, component):
        i = self.components.index(component)
        if i > 0:
            del self.components[i]

    def draw(self, surace):
        for component in self.components:
            if component.isVisible():
                component.draw(surace)

    def findComponent(self, pos):
        for component in reversed(self.components):
            if component.isVisible() and component.rect.collidepoint(pos):
                return component
        return None

    def redefineRect(self, rect):
        self.rect = rect
        for component in self.components:
            component.redefineRect(rect)

    def mouseOver(self, mousePos):
        self.mouse_is_over = True
        component = self.findComponent(mousePos)
        if component != self._selectedComponent and self._selectedComponent is not None:
            self._selectedComponent.mouseLeft(mousePos)
        if component is not None:
            component.mouseOver(mousePos)
            self._selectedComponent = component

    def mouseLeft(self, mousePos):
        self.mouse_is_over = False
        if self._selectedComponent is not None:
            self._selectedComponent.mouseLeft(mousePos)

    def mouseDown(self, mousePos):
        component = self.findComponent(mousePos)
        if component != self._selectedComponent and self._selectedComponent is not None:
            self._selectedComponent.mouseLeft(mousePos)
        if component is not None:
            component.mouseDown(mousePos)
            self._selectedComponent = component

    def mouseUp(self, mousePos):
        if self._selectedComponent is not None:
            self._selectedComponent.mouseUp(mousePos)
            if not self._selectedComponent.rect.collidepoint(mousePos):
                # we released button outside of component - it would be nice to let it know mouse is not inside of it any more
                self._selectedComponent.mouseLeft(mousePos)
        component = self.findComponent(mousePos)
        if component is not None:
            # we released mouse over some other component - now it is turn for it to receive mouse over
            component.mouseOver(mousePos)


class CardsCollection(Collection):
    def __init__(self, rect):
        super(CardsCollection, self).__init__(rect)
        self.cards = {}
        self.selected_card_name = None
        self.selectedCardComponent = None

    def addCard(self, name, component):
        self.cards[name] = component
        component._visible = False
        super(CardsCollection, self).addComponent(component)

    def selectCard(self, name):
        if name in self.cards:
            if self.selectedCardComponent is not None:
                self.selectedCardComponent.setVisible(False)
            self.selectedCardComponent = self.cards[name]
            self.selectedCardComponent.setVisible(True)
            self.selected_card_name = name
            return self.selectedCardComponent
        return None

    def selectedCardName(self):
        return self.selected_card_name


class Image(Component):
    def __init__(self, rect, surface, h_alignment=ALIGNMENT.LEFT, v_alignment=ALIGNMENT.TOP):
        super(Image, self).__init__(rect)  # Call super constructor to store rectable
        self._surface = surface
        self.h_alignment = h_alignment
        self.v_alignment = v_alignment

    def getImage(self):
        return self._surface

    def setImage(self, surface):
        self._surface = surface

    def draw(self, surface):
        if self._surface is not None:
            x = self.rect.x
            y = self.rect.y

            if self.h_alignment == ALIGNMENT.CENTER:
                x = self.rect.centerx - self._surface.get_width() // 2
            elif self.h_alignment == ALIGNMENT.RIGHT:
                x = self.rect.right - self._surface.get_width()

            if self.v_alignment == ALIGNMENT.MIDDLE:
                y = self.rect.centery - self._surface.get_height() // 2
            elif self.h_alignment == ALIGNMENT.RIGHT:
                y = self.rect.bottom - self._surface.get_height()

            surface.blit(self._surface, (x, y))


class Label(Image):
    def __init__(self, rect, text, colour=None, font=None, h_alignment=ALIGNMENT.LEFT, v_alignment=ALIGNMENT.TOP):
        super(Label, self).__init__(rect, None, h_alignment, v_alignment)  # Call super constructor to store rectable
        self._text = text
        self.font = font
        self.colour = colour if colour is not None else pygame.color.THECOLORS['white']

    def getText(self):
        return self._text

    def setText(self, text):
        if self._text != text:
            self._text = text
            self._surface = None

    def invalidateSurface(self):
        self._surface = None

    def draw(self, surface):
        if self._surface is None:
            self._surface = self._font().render(self._text, 0, self.colour)

        super(Label, self).draw(surface)


class Button(Component):
    def __init__(self, rect, onClick=None, onHover=None, label=None, background_decoration=None, mouse_over_decoration=None):
        super(Button, self).__init__(rect)  # Call super constructor to store rectable
        self.onClick = onClick
        self.onHover = onHover
        self._label = label
        self.background_decoration = background_decoration
        self.mouse_over_decoration = mouse_over_decoration
        self.redefineRect(rect)

    def getLabel(self):
        return self._label

    def setLabel(self, label):
        self._label = label
        self._label.redefineRect(self.rect)

    def redefineRect(self, rect):
        super(Button, self).redefineRect(rect)
        if self._label is not None:
            self._label.redefineRect(rect)  # set label's position to buttons
        if self.background_decoration is not None:
            self.background_decoration.redefineRect(rect)
        if self.mouse_over_decoration is not None:
            self.mouse_over_decoration.redefineRect(rect)

    def draw(self, surface):
        if self.mouse_is_over:
            if self.mouse_over_decoration is not None:
                self.mouse_over_decoration.draw(surface)
        else:
            if self.background_decoration is not None:
                self.background_decoration.draw(surface)

        if self._label is not None:  # this way 'label' can be anything - text, image or something custom drawn
            self._label.draw(surface)

    def mouseUp(self, mousePos):
        if self.rect.collidepoint(mousePos) and self.onClick is not None:
            self.onClick(self, mousePos)


class UIAdapter:
    def __init__(self, screen):
        self.topComponent = None
        self.mouseIsDown = False
        self.screen = screen

    def getScreen(self):
        return self.screen

    def setTopComponent(self, component):
        self.topComponent = component

    def processEvent(self, event):
        if event.type == pygame.MOUSEMOTION:
            mousePos = pygame.mouse.get_pos()
            self.mouseMoved(mousePos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mousePos = pygame.mouse.get_pos()
            self.mouseDown(mousePos)
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            mousePos = pygame.mouse.get_pos()
            self.mouseUp(mousePos)

    def mouseMoved(self, mousePos):
        if self.topComponent is not None:
            self.topComponent.mouseOver(mousePos)

    def mouseDown(self, mousePos):
        self.mouseIsDown = True
        if self.topComponent is not None:
            self.topComponent.mouseDown(mousePos)

    def mouseUp(self, mousePos):
        self.mouseIsDown = False
        if self.topComponent is not None:
            self.topComponent.mouseUp(mousePos)

    def draw(self, surface):
        if self.topComponent is not None:
            self.topComponent.draw(surface)


class UI_HINT:
    NORMAL = 1
    WARNING = 2
    ERROR = 3


class BaseUIFactory:
    def __init__(self):
        pass

    def label(self, rect, text, font=None, colour=None, h_alignment=ALIGNMENT.LEFT, v_alignment=ALIGNMENT.TOP, hint=UI_HINT.NORMAL):
        return None

    def image(self, rect, image, hint=UI_HINT.NORMAL):
        return None

    def button(self, rect, onClick=None, onHover=None, label=None, hint=UI_HINT.NORMAL):
        return None

    def text_button(self, rect, text, onClick=None, onHover=None, hint=UI_HINT.NORMAL):
        return self.button(rect, onClick, onHover, self.label(None, text, h_alignment=ALIGNMENT.CENTER, v_alignment=ALIGNMENT.MIDDLE), hint=hint)
