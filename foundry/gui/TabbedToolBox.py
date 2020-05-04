from typing import Union

from PySide2.QtCore import Signal, SignalInstance
from PySide2.QtWidgets import QScrollArea, QTabWidget

from foundry.game.gfx.objects.EnemyItem import EnemyObject
from foundry.game.gfx.objects.LevelObject import LevelObject
from foundry.gui.ObjectToolBox import ObjectIcon, ObjectToolBox


class TabbedToolBox(QTabWidget):
    object_icon_clicked: SignalInstance = Signal(ObjectIcon)

    def __init__(self, parent=None):
        super(TabbedToolBox, self).__init__(parent)

        self.setTabPosition(self.South)

        self._recent_toolbox = ObjectToolBox(self)
        self._recent_toolbox.object_icon_clicked.connect(self.object_icon_clicked)
        self._recent_toolbox.object_placed.connect(self._on_object_dragged)

        self._objects_toolbox = ObjectToolBox(self)
        self._objects_toolbox.object_icon_clicked.connect(self.object_icon_clicked)
        self._objects_toolbox.object_placed.connect(self._on_object_dragged)

        self._enemies_toolbox = ObjectToolBox(self)
        self._enemies_toolbox.object_icon_clicked.connect(self.object_icon_clicked)
        self._enemies_toolbox.object_placed.connect(self._on_object_dragged)

        self._object_scroll_area = QScrollArea(self)
        self._object_scroll_area.setWidgetResizable(True)
        self._object_scroll_area.setWidget(self._objects_toolbox)

        self._enemies_scroll_area = QScrollArea(self)
        self._enemies_scroll_area.setWidgetResizable(True)
        self._enemies_scroll_area.setWidget(self._enemies_toolbox)

        self.addTab(self._recent_toolbox, "Recent")
        self.addTab(self._object_scroll_area, "Objects")
        self.addTab(self._enemies_scroll_area, "Enemies")

        self.show_level_object_tab()

    def show_recent_tab(self):
        self.setCurrentIndex(self.indexOf(self._recent_toolbox))

    def show_level_object_tab(self):
        self.setCurrentIndex(self.indexOf(self._object_scroll_area))

    def show_enemy_item_tab(self):
        self.setCurrentIndex(self.indexOf(self._enemies_scroll_area))

    def select_object(self, level_object):
        recent_tab_showing = self.currentIndex() == self.indexOf(self._recent_toolbox)

        if self._recent_toolbox.has_object(level_object) and recent_tab_showing:
            pass
        elif isinstance(level_object, LevelObject):
            self.show_level_object_tab()
        elif isinstance(level_object, EnemyObject):
            self.show_enemy_item_tab()

    def set_object_set(self, object_set_index, graphic_set_index=-1):
        self._recent_toolbox.clear()
        self._objects_toolbox.clear()
        self._objects_toolbox.add_from_object_set(object_set_index, graphic_set_index)

        self._enemies_toolbox.clear()
        self._enemies_toolbox.add_from_enemy_set(object_set_index)

    def add_recent_object(self, level_object: Union[EnemyObject, LevelObject]):
        self._recent_toolbox.place_at_front(level_object)

    def _on_object_dragged(self, object_icon: ObjectIcon):
        self.add_recent_object(object_icon.object)
