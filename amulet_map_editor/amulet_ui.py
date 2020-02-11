import wx
from typing import Dict
from amulet_map_editor.amulet_wx.world_select import WorldSelectWindow
from amulet_map_editor import lang, config
from amulet_map_editor.amulet_wx.world_manager import WorldManagerUI
from amulet_map_editor.amulet_wx import wx_util


class AmuletMainWindow(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(
            self,
            parent,
            id=wx.ID_ANY,
            title="Amulet Converter V0.1", # TODO: set this dynamically
            pos=wx.DefaultPosition,
            size=wx.Size(560, 400),
            style=wx.CAPTION
            | wx.CLOSE_BOX
            | wx.MINIMIZE_BOX
            | wx.MAXIMIZE_BOX
            | wx.MAXIMIZE
            | wx.SYSTEM_MENU
            | wx.TAB_TRAVERSAL
            | wx.CLIP_CHILDREN
            | wx.RESIZE_BORDER,
        )

        self._open_worlds: Dict[str, WorldManagerUI] = {}

        self.world_tab_holder = wx.Notebook(
            self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0
        )

        self._main_menu = AmuletMainMenu(self.world_tab_holder, self._open_world)

        self._add_world_tab(
            self._main_menu,
            lang.get('main_menu')
        )

        self.Bind(wx.EVT_CLOSE, self._on_close)

        self.Show()

    def _add_world_tab(self, obj, obj_name):
        # TODO: find a way for the tab to be optionally closeable
        self.world_tab_holder.AddPage(obj, obj_name, True)

    def _open_world(self, path: str):
        """Open a world panel add add it to the notebook"""
        world = WorldManagerUI(self.world_tab_holder, path)
        self._open_worlds[path] = world
        self._add_world_tab(world, world.world_name)
        self._main_menu.Enable()

    def close_world(self, path: str):
        """Close a given world and remove it from the notebook"""
        if path in self._open_worlds:
            world = self._open_worlds[path]
            self.world_tab_holder.DeletePage(
                self.world_tab_holder.FindPage(world)
            )
            world.close_world()
            del self._open_worlds[path]

    def _on_close(self, evt):
        close = True
        for path, world in list(self._open_worlds.items()):
            if world.is_closeable():
                self.close_world(path)
            else:
                close = False
        if close:
            evt.Skip()
        else:
            wx.MessageBox(
                'A world is still being used. Please close it first'
            )


class AmuletMainMenu(wx_util.SimplePanel):
    def __init__(self, parent, open_world):
        super(AmuletMainMenu, self).__init__(
            parent
        )
        self._open_world_callback = open_world
        amulet_converter = wx.StaticText(
            self,
            wx.ID_ANY,
            'Amulet Converter',
            wx.DefaultPosition,
            wx.DefaultSize,
            0,
        )
        amulet_converter.SetFont(wx.Font(40, wx.DECORATIVE, wx.NORMAL, wx.NORMAL))
        self.add_object(
            amulet_converter, 0, wx.ALL|wx.CENTER
        )
        self._open_world_button = wx.Button(self, wx.ID_ANY, label='Select World')
        self._open_world_button.Bind(wx.EVT_BUTTON, self._show_world_select)
        self.add_object(self._open_world_button, 0, wx.ALL|wx.CENTER)

    def _show_world_select(self, evt):
        self.Disable()
        WorldSelectWindow(self._open_world_callback, self.Enable)


if __name__ == "__main__":
    app = wx.App()
    frame = AmuletMainWindow(None)
    app.MainLoop()
    config.save()