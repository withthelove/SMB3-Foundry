from typing import List, Optional, Tuple

from PySide6.QtCore import QPoint, QSize
from PySide6.QtGui import QCursor, QKeySequence, QMouseEvent, QPainter, QPixmap, QShortcut, QUndoStack, Qt
from PySide6.QtWidgets import QToolTip, QWidget

from foundry import get_level_thumbnail
from foundry.game.ObjectSet import OBJECT_SET_NAMES
from foundry.game.gfx.drawable.Block import get_worldmap_tile
from foundry.game.gfx.objects import LevelObject, MapTile
from foundry.game.gfx.objects.world_map.map_object import MapObject
from foundry.game.level.LevelRef import LevelRef
from foundry.game.level.WorldMap import WorldMap
from foundry.gui.MainView import (
    MODE_DRAG,
    MODE_FREE,
    MODE_PLACE_TILE,
    MODE_SELECTION_SQUARE,
    MainView,
)
from foundry.gui.WorldDrawer import WorldDrawer
from foundry.gui.settings import SETTINGS
from scribe.gui.commands import (
    SetEnemyAddress,
    SetLevelAddress,
    SetObjectSet,
    SetSpriteItem,
    SetSpriteType,
    MoveMapObject,
    MoveTile,
    PutTile,
)
from scribe.gui.world_view_context_menu import WorldContextMenu
from smb3parse.constants import TILE_MUSHROOM_HOUSE_1, TILE_MUSHROOM_HOUSE_2, TILE_NAMES, TILE_SPADE_HOUSE
from smb3parse.data_points import Position
from smb3parse.levels import FIRST_VALID_ROW, WORLD_MAP_BLANK_TILE_ID, WORLD_MAP_HEIGHT


class WorldView(MainView):
    context_menu: WorldContextMenu

    def __init__(self, parent: Optional[QWidget], level: LevelRef, context_menu: Optional[WorldContextMenu] = None):
        super(WorldView, self).__init__(parent, level, context_menu)

        self.drawer = WorldDrawer()

        self.draw_level_pointers = SETTINGS["draw_level_pointers"]
        """Whether to highlight the spaces, which can be used to point to levels."""
        self.draw_sprites = SETTINGS["draw_overworld_sprites"]
        """Whether to draw overworld sprites, like hammer bros and the 'help' speech bubble."""
        self.draw_start = SETTINGS["draw_starting_position"]
        """Whether to highlight the space, that the player starts on, when first coming into the world."""
        self.draw_airship_points = SETTINGS["draw_airship_points"]
        """Whether to show the points and airship can retreat to."""
        self.draw_pipes = SETTINGS["draw_pipes"]
        """Whether to draw positions marked as pipe entrances."""
        self.draw_locks = SETTINGS["draw_locks"]
        """Whether to highlight positions marked as having locks."""

        self.display_level_preview = False

        self._tile_to_put: int = WORLD_MAP_BLANK_TILE_ID

        self.selection_square.set_offset(0, FIRST_VALID_ROW)

        self.mouse_mode = MODE_FREE

        self.drag_start_point = Position.from_xy(0, 0)
        self.last_mouse_position = Position.from_xy(0, 0)

        self.selected_object: Optional[MapObject] = None

        self.dragging_happened = False

        # TODO: update
        self.setWhatsThis(
            "<b>Level View</b><br/>"
            "This renders the level as it would appear in game plus additional information, that can be "
            "toggled in the View menu.<br/>"
            "It supports selecting multiple objects, moving, copy/pasting and resizing them using the "
            "mouse or the usual keyboard shortcuts.<br/>"
            "There are still occasional rendering errors, or small inconsistencies. If you find them, "
            "please report the kind of object (name or values in the SpinnerPanel) and the level or "
            "object set they appear in, in the discord and @Michael or on the github page under Help."
            "<br/><br/>"
            ""
            "If all else fails, click the play button up top to see your level in game in seconds."
        )

        QShortcut(QKeySequence(Qt.CTRL + Qt.Key_A), self, self.select_all)

    @property
    def draw_grid(self):
        return self.drawer.draw_grid

    @draw_grid.setter
    def draw_grid(self, value):
        self.drawer.draw_grid = value

    @property
    def draw_level_pointers(self):
        return self.drawer.draw_level_pointers

    @draw_level_pointers.setter
    def draw_level_pointers(self, value):
        self.drawer.draw_level_pointers = value

    @property
    def draw_sprites(self):
        return self.drawer.draw_sprites

    @draw_sprites.setter
    def draw_sprites(self, value):
        self.drawer.draw_sprites = value

    @property
    def draw_start(self):
        return self.drawer.draw_start

    @draw_start.setter
    def draw_start(self, value):
        self.drawer.draw_start = value

    @property
    def draw_airship_points(self):
        return self.drawer.draw_airship_points

    @draw_airship_points.setter
    def draw_airship_points(self, value):
        self.drawer.draw_airship_points = value

    @property
    def draw_pipes(self):
        return self.drawer.draw_pipes

    @draw_pipes.setter
    def draw_pipes(self, value):
        self.drawer.draw_pipes = value

    @property
    def draw_locks(self):
        return self.drawer.draw_locks

    @draw_locks.setter
    def draw_locks(self, value):
        self.drawer.draw_locks = value

    @property
    def undo_stack(self) -> QUndoStack:
        return self.window().findChild(QUndoStack, "undo_stack")

    @property
    def world(self) -> WorldMap:
        return self.level_ref.level

    def set_mouse_mode(self, new_mode: int, event: Optional[QMouseEvent]):
        if new_mode == MODE_PLACE_TILE:
            tile_pixmap = QPixmap(QSize(self.block_length, self.block_length))

            painter = QPainter(tile_pixmap)
            get_worldmap_tile(self._tile_to_put).draw(painter, 0, 0, self.block_length)
            painter.end()

            self.setCursor(QCursor(tile_pixmap))

        elif new_mode == MODE_SELECTION_SQUARE:
            if event is None:
                return

            self.selection_square.start(event.pos())

        elif new_mode == MODE_DRAG:
            if event is None:
                return

            self.drag_start_point = Position.from_xy(*self._to_level_point(event.pos()))
            self.last_mouse_position = self.drag_start_point
            self.setCursor(Qt.ClosedHandCursor)

        elif new_mode == MODE_FREE:
            self._tile_to_put = WORLD_MAP_BLANK_TILE_ID

            self._object_was_selected_on_last_click = False
            self.setCursor(Qt.ArrowCursor)

        self.mouse_mode = new_mode

    def on_put_tile(self, tile_id: int):
        self._tile_to_put = tile_id
        self.set_mouse_mode(MODE_PLACE_TILE, None)

    def mouseMoveEvent(self, event: QMouseEvent):
        should_display_level = self.mouse_mode == MODE_FREE and self.display_level_preview

        if should_display_level and not self._set_level_thumbnail(event):
            # clear tooltip if supposed to show one, but no level thumbnail was available (e.g. no level there)
            self.setCursor(Qt.ArrowCursor)

            self.setToolTip("")
            QToolTip.hideText()

        if self.read_only:
            return super(WorldView, self).mouseMoveEvent(event)

        if self.mouse_mode == MODE_PLACE_TILE and event.buttons() & Qt.LeftButton:
            x, y = self._to_level_point(event.pos())

            tile = self.world.object_at(x, y)

            if tile is not None and tile.type != self._tile_to_put:
                self.undo_stack.push(PutTile(self.world, Position.from_xy(x, y), self._tile_to_put))
                self.update()
        elif self.mouse_mode == MODE_DRAG:
            self._dragging(event)

        elif self.selection_square.active:
            self._set_selection_end(event.pos())

        return super(WorldView, self).mouseMoveEvent(event)

    def _set_level_thumbnail(self, event: QMouseEvent):
        if self.mouse_mode != MODE_FREE:
            return False

        x, y = self._to_level_point(event.pos())

        if self.world.tile_at(x, y) in [TILE_SPADE_HOUSE, TILE_MUSHROOM_HOUSE_1, TILE_MUSHROOM_HOUSE_2]:
            return False

        if (level_pointer := self.world.level_pointer_at(x, y)) is None:
            return False

        self.setCursor(Qt.PointingHandCursor)

        try:
            level_name = self.world.level_name_at_position(x, y)

            object_set_name = OBJECT_SET_NAMES[level_pointer.data.object_set]

            image_data = get_level_thumbnail(
                level_pointer.data.object_set, level_pointer.data.level_address, level_pointer.data.enemy_address
            )

            self.setToolTip(
                f"<b>{level_name}</b><br/>"
                f"<u>Type:</u> {object_set_name} "
                f"<u>Objects:</u> {level_pointer.data.level_address} "
                f"<u>Enemies:</u> {level_pointer.data.enemy_address}<br/>"
                f"<img src='data:image/png;base64,{image_data}'>"
            )

            return True
        except ValueError:
            return False

    def _on_right_mouse_button_up(self, event):
        self.set_mouse_mode(MODE_FREE, event)

    def _fill_tile(self, tile_to_fill_in: int, x, y):
        if tile_to_fill_in == self._tile_to_put:
            return

        if x < 0 or x >= self.world.internal_world_map.width:
            return

        if y < FIRST_VALID_ROW or y >= FIRST_VALID_ROW + WORLD_MAP_HEIGHT:
            return

        if (tile := self.world.object_at(x, y)) is not None and tile.type == tile_to_fill_in:
            self.undo_stack.push(PutTile(self.world, Position.from_xy(x, y), self._tile_to_put))
        else:
            return

        self._fill_tile(tile_to_fill_in, x + 1, y)
        self._fill_tile(tile_to_fill_in, x - 1, y)
        self._fill_tile(tile_to_fill_in, x, y + 1)
        self._fill_tile(tile_to_fill_in, x, y - 1)

    def _to_level_point(self, q_point) -> Tuple[int, int]:
        x, y = super(WorldView, self)._to_level_point(q_point)

        return x, y + FIRST_VALID_ROW

    def _visible_object_at(self, point: QPoint) -> MapObject:
        level_x, level_y = self._to_level_point(point)

        obj = None

        if self.draw_pipes:
            obj = self.world.pipe_at(level_x, level_y)

        if not obj and self.draw_locks:
            obj = self.world.locks_at(level_x, level_y)

        if not obj and self.draw_airship_points:
            obj = self.world.airship_point_at(level_x, level_y, self.draw_airship_points)

        if not obj and self.draw_sprites:
            obj = self.world.sprite_at(level_x, level_y)

        if not obj and self.draw_level_pointers:
            obj = self.world.level_pointer_at(level_x, level_y)

        if not obj:
            obj = self.world.objects[Position.from_xy(level_x, level_y).tile_data_index]

        assert obj is not None

        return obj

    def _on_left_mouse_button_down(self, event: QMouseEvent):
        x, y = self._to_level_point(event.pos())

        if not self.level_ref.point_in(x, y):
            return

        if self.mouse_mode == MODE_PLACE_TILE:
            tile = self.world.object_at(x, y)

            assert tile is not None

            tile_to_put_name = TILE_NAMES[self._tile_to_put]

            if event.modifiers() & Qt.ShiftModifier:
                self.undo_stack.beginMacro(f"Fill in '{tile.name}' with '{tile_to_put_name}'")
                self._fill_tile(tile.type, x, y)
            else:
                self.undo_stack.beginMacro(f"Place '{tile_to_put_name}'")
                self.undo_stack.push(PutTile(self.world, Position.from_xy(x, y), self._tile_to_put))

            self.update()

            return

        if event.modifiers() & Qt.ControlModifier:
            self.set_mouse_mode(MODE_SELECTION_SQUARE, event)
            return

        obj = self._visible_object_at(event.pos())

        if not obj.selected and not event.modifiers() & Qt.ShiftModifier:
            self._select_object(None)

        if obj and obj.selected:
            pass
        else:
            self.select_object_like(obj)

        self.set_mouse_mode(MODE_DRAG, event)

    def _dragging(self, event: QMouseEvent):
        level_pos = Position.from_xy(*self._to_level_point(event.pos()))
        diff_pos = level_pos - self.last_mouse_position

        dx, dy = diff_pos.xy

        if dx == dy == 0:
            return

        self.dragging_happened = True

        self.last_mouse_position = level_pos

        for selected_obj in self.get_selected_objects():
            selected_obj.move_by(dx, dy)

        if not self.get_selected_objects() and self.selected_object:
            self.selected_object.move_by(dx, dy)

        self.level_ref.data_changed.emit()
        self.update()

    def _on_left_mouse_button_up(self, event: QMouseEvent):
        if self.mouse_mode == MODE_PLACE_TILE:
            self.undo_stack.endMacro()
            return

        obj = self.object_at(event.pos())

        if self.mouse_mode == MODE_DRAG and self.dragging_happened:
            drag_end_point = Position.from_xy(*self._to_level_point(event.pos()))

            if self.get_selected_objects():
                self._move_selected_tiles(drag_end_point)

            if self.selected_object and not isinstance(self.selected_object, MapTile):
                self.undo_stack.push(
                    MoveMapObject(self.world, self.selected_object, start=self.drag_start_point, end=drag_end_point)
                )

            self.dragging_happened = False

        elif self.selection_square.active:
            self._stop_selection_square()

        elif obj and obj.selected and not self._object_was_selected_on_last_click:
            # handle selected object on release to allow dragging

            if event.modifiers() & Qt.ControlModifier:
                # take selected object under cursor out of current selection
                selected_objects = self.get_selected_objects().copy()
                selected_objects.remove(obj)
                self.select_objects(selected_objects, replace_selection=True)
            else:
                # replace selection with only selected object
                self.select_objects([obj], replace_selection=True)

        self.set_mouse_mode(MODE_FREE, event)

    def _move_selected_tiles(self, drag_end_point: Position):
        dx, dy = (drag_end_point - self.drag_start_point).xy

        if dx == dy == 0:
            return

        sel_objects = self.get_selected_objects().copy()

        self.select_objects([], replace_selection=True)

        if (no_of_sel_objects := len(sel_objects)) > 1:
            self.undo_stack.beginMacro(f"Move {no_of_sel_objects} Tiles")

        old_objects = self.world.objects.copy()

        for selected_obj in reversed(sel_objects):
            if not isinstance(selected_obj, MapTile):
                continue

            end = selected_obj.pos.copy()

            selected_obj.move_by(-dx, -dy)

            start = selected_obj.pos.copy()

            # we don't actually move the map position in the end, just change the type at both positions

            # if we are moving only one tile, then move it back, if more, reset them
            if no_of_sel_objects > 1 or self.world.point_in(*end.xy):
                cmd = MoveTile(self.world, start, old_objects[start.tile_data_index].type, end)

                self.undo_stack.push(cmd)

        if no_of_sel_objects > 1:
            self.undo_stack.endMacro()

    def _set_selection_end(self, position, always_replace_selection=False):
        return super(WorldView, self)._set_selection_end(position, True)

    def select_object_like(self, obj: MapObject):
        if self.selected_object is not None:
            self.selected_object.selected = False

        if obj is None:
            return

        self.selected_object = obj
        self.selected_object.selected = True

        self.update()

    def select_sprite(self, index: int):
        self.select_object_like(self.world.sprites[index])

    def select_level_pointer(self, index: int):
        self.select_object_like(self.world.level_pointers[index])

    def clear_tiles(self):
        self.undo_stack.beginMacro("Clear Tiles")

        for map_tile in self.world.get_all_objects():
            self.undo_stack.push(PutTile(self.world, map_tile.pos, WORLD_MAP_BLANK_TILE_ID))

        self.undo_stack.endMacro()

    def clear_sprites(self):
        self.undo_stack.beginMacro("Clear Sprites")

        for sprite in self.world.sprites:
            self.undo_stack.push(SetSpriteType(sprite.data, 0))
            self.undo_stack.push(SetSpriteItem(sprite.data, 0))
            self.undo_stack.push(MoveMapObject(self.world, sprite, Position.from_xy(0, FIRST_VALID_ROW)))

        self.undo_stack.endMacro()

    def clear_level_pointers(self):
        self.undo_stack.beginMacro("Clear Level Pointers")

        for level_pointer in self.world.level_pointers:
            self.undo_stack.push(SetLevelAddress(level_pointer.data, 0))
            self.undo_stack.push(SetEnemyAddress(level_pointer.data, 0))
            self.undo_stack.push(SetObjectSet(level_pointer.data, 0))
            self.undo_stack.push(MoveMapObject(self.world, level_pointer, Position.from_xy(0, FIRST_VALID_ROW)))

        self.undo_stack.endMacro()

    def remove_selected_objects(self):
        for obj in self.level_ref.selected_objects:
            self.level_ref.remove_object(obj)

    def scroll_to_objects(self, objects: List[LevelObject]):
        if not objects:
            return

        min_x = min([obj.x_position for obj in objects]) * self.block_length
        min_y = min([obj.y_position for obj in objects]) * self.block_length

        self.parent().parent().ensureVisible(min_x, min_y)
