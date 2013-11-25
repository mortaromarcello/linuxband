#!/usr/env python

import sys, os
from gi.repository import GObject, Gtk, Gdk, Pango, PangoCairo
import cairo
import math
import logging
import gettext
import locale
PKG_DATA_DIR = os.getcwd() + "/../../"
PKG_LIB_DIR = os.getcwd() + "/lib"
sys.path.insert(0, PKG_DATA_DIR)
from linuxband.glob import Glob
from linuxband.logger import Logger
from linuxband.config import Config
from linuxband.mma.song import Song
from linuxband.midi.mma2smf import MidiGenerator
from linuxband.midi.midi_player import MidiPlayer
LOCAL_DIR = 'locale'
PACKAGE_NAME = "linuxband"
PACKAGE_VERSION = "12.02.1"
locale.setlocale(locale.LC_ALL, '')
gettext.bindtextdomain(PACKAGE_NAME, LOCAL_DIR)
gettext.textdomain(PACKAGE_NAME)
_ = gettext.gettext

class Gui():
  ui = '''
  <ui>
    <menubar name="MenuBar">
      <menu action="File">
        <menuitem action="New"/>
        <menuitem action="Open"/>
        <menuitem action="Recent"/>
        <menuitem action="Save"/>
        <menuitem action="Save-as"/>
        <menuitem action="Export-midi"/>
        <menuitem action="Quit"/>
      </menu>
      <menu action="Edit">
        <menuitem action="Cut"/>
        <menuitem action="Copy"/>
        <menuitem action="Paste"/>
        <menuitem action="Delete"/>
        <menuitem action="Select-all"/>
      </menu>
      <menu action="View">
        <menuitem action="Chordsheet"/>
        <menuitem action="MMA"/>
      </menu>
      <menu action="Help">
      </menu>
    </menubar>
    <toolbar name="Toolbar">
      <toolitem action="New"/>
      <toolitem action="Open"/>
      <toolitem action="Save"/>
      <toolitem action="Quit"/>
      <separator/>
      <toolitem action="Play"/>
      <toolitem action="Stop"/>
      <toolitem action="Pause"/>
    </toolbar>
  </ui>
  '''

  def __init__(self):
    win = Gtk.Window()
    win.connect("delete-event", Gtk.main_quit)
    self.__config = Config()
    self.__config.load_config()
    self.__song = Song(MidiGenerator(self.__config))
    self.__midi_player = MidiPlayer(self)
    if (self.__config.get_jack_connect_startup()):
      self.__midi_player.startup()
    self.__save_changes_dialog = Gtk.MessageDialog(type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.YES_NO)
    self.__open_file_dialog = Gtk.FileChooserDialog(_('Open MMA file'), None, Gtk.FileChooserAction.OPEN, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN,Gtk.ResponseType.OK))
    self.__mma_filter = Gtk.FileFilter()
    self.__mma_filter.set_name(_("MMA files"))
    self.__mma_filter.add_pattern("*.mma")
    self.__any_filter = Gtk.FileFilter()
    self.__any_filter.set_name(_("Any file"))
    self.__any_filter.add_pattern("*")
    self.__open_file_dialog.add_filter(self.__mma_filter)
    self.__open_file_dialog.add_filter(self.__any_filter)
    self.__save_as_dialog = Gtk.FileChooserDialog(_('Save the song as'), None, Gtk.FileChooserAction.SAVE, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN,Gtk.ResponseType.OK))
    self.__save_as_dialog.add_filter(self.__mma_filter)
    self.__save_as_dialog.add_filter(self.__any_filter)
    self.init_gui(win)
    win.show_all()
    self.__do_new_file()

  def init_gui(self, win):
    """ inizializza l'interfaccia """
    vbox = Gtk.VBox()
    #hbox = Gtk.HBox()
    win.add(vbox)
    self.__chord_sheet = self.ChordSheet(self.__song, self.__config)
    self.uimanager = Gtk.UIManager()
    accelgroup = self.uimanager.get_accel_group()
    win.add_accel_group(accelgroup)
    actiongroup = Gtk.ActionGroup('Linuxband')
    actiongroup.add_actions([('Quit', Gtk.STOCK_QUIT, _('_Quit me!'), None, _('Quit the Program'), self.application_end_event_callback),
                              ('New', Gtk.STOCK_NEW, _('_New'), None, _('New file'), self.new_file_callback),
                              ('Open', Gtk.STOCK_OPEN, _('_Open'), None, _('Open file'), self.open_file_callback),
                              ('Recent', Gtk.STOCK_OPEN, _('_Recent songs'), None, _('Recent songs')),
                              ('Save', Gtk.STOCK_SAVE, _('_Save'), None, _('Save file'), self.save_file_callback),
                              ('Save-as', Gtk.STOCK_SAVE_AS, _('Save _as'), None, _('Save as'), self.save_file_as_callback),
                              ('Export-midi', Gtk.STOCK_SAVE_AS, _('Export midi'), None, _('Export to midi file'), self.export_midi_callback),
                              ('Cut', Gtk.STOCK_CUT, _('Cut'), None),
                              ('Copy', Gtk.STOCK_COPY, _('Copy'), None),
                              ('Paste', Gtk.STOCK_PASTE, _('Paste'), None),
                              ('Delete', Gtk.STOCK_DELETE, _('Delete'), None),
                              ('Select-all', Gtk.STOCK_SELECT_ALL, _('Select all'), None),
                              ('File', None, _('_File')),
                              ('Edit', None, _('Edit')),
                              ('View', None, _('_View')),
                              ('Help', None, _('_Help'))])
    actiongroup.get_action('Quit').set_property('short-label', _('_Quit'))
    actiongroup.add_radio_actions([('Chordsheet', None, _('C_hordsheet'), '<Control>h', _('Chordsheet'), 0),
                                  ('MMA', None, _('MMA source'), '<Control>m', _('MMA source'), 1), ], 0, self.switch_view_callback)
    actiongroup.add_toggle_actions([('Play', Gtk.STOCK_MEDIA_PLAY, None, None, _('Play song [Space]. If Ctrl key is held down, will play from current bar. If Shift is held down, will play selected bars. If Ctrl+Shift is held down, only compiles the song and reports errors if any')),
                              ('Stop', Gtk.STOCK_MEDIA_STOP, None, None, _('Stop playback [Space]'), self.playback_stop_callback),
                              ('Pause', Gtk.STOCK_MEDIA_PAUSE, None, None, _('Pause playback'),  self.playback_pause_callback)])
    self.uimanager.insert_action_group(actiongroup, 0)
    self.uimanager.add_ui_from_string(self.ui)
    menubar = self.uimanager.get_widget('/MenuBar')
    vbox.pack_start(menubar, False, False, 0)
    toolbar = self.uimanager.get_widget('/Toolbar')
    self.uimanager.get_widget('/MenuBar/Help').set_right_justified( True)
    self.uimanager.get_widget('/Toolbar/Play').get_children()[0].connect('button-press-event', self.playback_start)
    vbox.pack_start(toolbar, False, False, 0)
    notebook = Gtk.Notebook()
    vbox_notebook = Gtk.VBox()
    vbox_notebook.pack_start(self.__chord_sheet, True, True, 0)
    notebook.append_page(vbox_notebook, None)
    vbox.pack_start(notebook, True, True, 0)

  def move_playhead_to_bar(self, barNum):
    """ Called by MidiPlayer. """
    self.__chord_sheet.move_playhead_to(barNum)

  def move_playhead_to_line(self, lineNum):
    """ Called by MidiPlayer. """
    #self.__source_editor.move_playhead_to(lineNum)

  def hide_playhead(self):
    """ Called by MidiPlayer. """
    self.__chord_sheet.move_playhead_to(-1)
    #self.__source_editor.move_playhead_to(-1)

  def playback_start(self, button, event):
    """ Play. """
    if event.get_state() & Gdk.ModifierType.SHIFT_MASK and event.get_state() & Gdk.ModifierType.CONTROL_MASK:
      self.__compile_song(True)
    else:
      player = self.__midi_player
      res = self.__compile_song(True)
      if res == 0:
        res, midi_data = self.__song.get_playback_midi_data()
        player.playback_stop()
        if res != 0: # generate SMF failed
            if res > 0 or res == -1: self.__show_mma_error(res)
            return
        player.load_smf_data(midi_data, self.__song.get_data().get_mma_line_offset())
      else:
        return
      self.__enable_pause_button();
      if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
        player.playback_start_bar(self.__chord_sheet.get_current_bar_number())
      elif event.get_state() & Gdk.ModifierType.SHIFT_MASK:
        player.playback_start_bars(self.__chord_sheet.get_selection_limits())
      else:
        player.playback_start()

  def playback_stop_callback(self, button=None):
    """ Stop. """
    self.__enable_pause_button();
    self.__midi_player.playback_stop()

  __ignore_toggle = False
  def playback_pause_callback(self, button=None):
    """ Pause. """
    if Gui.__ignore_toggle:
      Gui.__ignore_toggle = False
    else:
      self.__midi_player.set_pause(button.get_active());

  def refresh_chord_sheet(self):
    """ Refresh chord sheet """
    self.__set_song_bar_count(self.__song.get_data().get_bar_count())

  def application_end_event_callback(self, *args):
    """ Signal handler for delete_event in GtkWindow 'mainWindow' """
    self.__do_application_end()
    return True
    
  def new_file_callback(self, menuitem):
    """ New. Signal handler for activate in GtkAction 'imagemenuitem1' stock-id=gtk-new """
    if self.__handle_unsaved_changes():
      self.__do_new_file()
      
  def open_file_callback(self, menuitem):
    """ Open. Signal handler for activate in GtkAction 'imagemenuitem2' stock-id= gtk-open """
    if self.__handle_unsaved_changes():
      if (self.__open_file_dialog.get_current_folder() <> self.__config.get_work_dir()):
        self.__open_file_dialog.set_current_folder(self.__config.get_work_dir())
    result = self.__open_file_dialog.run()
    self.__open_file_dialog.hide()
    if (result == Gtk.ResponseType.OK):
      self.__config.set_work_dir(self.__open_file_dialog.get_current_folder())
      full_name = self.__open_file_dialog.get_filename()
    #  manager = Gtk.RecentManager.get_default()
    #  manager.add_item('file://' + full_name)
      self.__input_file = full_name
      self.__output_file = full_name
      self.__do_open_file()

  def save_file_callback(self, menuitem):
    """ Save. Signal handler for activate in GtkAction 'imagemenuitem3' stock-id= gtk-save """
    self.__do_save_file()

  def save_file_as_callback(self, menuitem):
    """ Save as. Signal handler for activate in GtkAction 'imagemenuitem4' stock-id= gtk-save-as """
    self.__do_save_as()

  def export_midi_callback(self, menuitem):
    
    """ Export MIDI. Signal handler for activate in GtkAction 'menuitem8' stock-id= gtk-save-as """
    #if self.__compile_song(True) == 0:
    #  if (self.__export_midi_dialog.get_current_folder() <> self.__config.get_work_dir()):
    #    self.__export_midi_dialog.set_current_folder(self.__config.get_work_dir())
    #  out_file = self.__output_file if self.__output_file else Glob.OUTPUT_FILE_DEFAULT
    #  out_file = self.__change_extension(out_file, "mid")
    #  logging.debug(out_file)
    #  self.__export_midi_dialog.set_current_name(out_file)
    #  result = self.__export_midi_dialog.run()
    #  self.__export_midi_dialog.hide()
    #  if (result == Gtk.ResponseType.OK):
    #    self.__config.set_work_dir(self.__export_midi_dialog.get_current_folder())
    #    full_name = self.__export_midi_dialog.get_filename()
    #    self.__song.write_to_midi_file(full_name)
    #else:
    #  logging.error("Failed to compile MMA file. Fix the errors and try the export again.")
    
  def __do_new_file(self):
    self.__output_file = None
    self.__input_file = self.__config.getTemplateFile()
    self.__do_open_file()

  def __do_open_file(self):
    """ """
    self.playback_stop_callback()
    self.__song.load_from_file(self.__input_file)
    res = self.__song.compile_song()
    self.__chord_sheet.new_song_loaded()
    #self.__source_editor.new_song_loaded(self.__song.write_to_string())
    self.refresh_chord_sheet()
    #self.__refresh_song_title()
    #if res > 0 or res == -1: self.__show_mma_error(res)

  def switch_view_callback(self, item=None):
    """ Signal handler for toggled in GtkRadioAction 'menuitem5' """
    #if Gui.__ignore_toggle2:
    #  Gui.__ignore_toggle2 = False
    #else:
    #  if self.__menuitem5.get_active():
    #    self.__notebook3.set_current_page(0)
    #  else:
    #    self.__notebook3.set_current_page(1)

  def __do_save_file(self):
    #if self.__output_file == None:
    #  return self.__do_save_as()
    #else:
    #  self.__compile_song(False)
    #  self.__song.write_to_mma_file(self.__output_file)
    return True

  def __handle_unsaved_changes(self):
    """ """
    if self.__song.get_data().is_save_needed():
      self.__save_changes_dialog.set_property("text", "Save changes to " + self.__song.get_data().get_title() + "?")
      self.__save_changes_dialog.set_property("secondary_text", "Your changes will be lost if you don't save them.")
      result = self.__save_changes_dialog.run()
      self.__save_changes_dialog.hide()
      if (result == gtk.ResponseType.YES):
        return self.__do_save_file()

  def __do_save_as(self):
    if (self.__save_as_dialog.get_current_folder() <> self.__config.get_work_dir()):
      self.__save_as_dialog.set_current_folder(self.__config.get_work_dir())
    self.__save_as_dialog.set_current_name(Glob.OUTPUT_FILE_DEFAULT)
    result = self.__save_as_dialog.run()
    self.__save_as_dialog.hide()
    if (result == Gtk.ResponseType.OK):
      self.__config.set_work_dir(self.__save_as_dialog.get_current_folder())
      full_name = self.__save_as_dialog.get_filename()
      self.__compile_song(False)
      self.__song.write_to_mma_file(full_name)
      self.__output_file = full_name
      return True
    else:
      return False

  def __do_application_end(self):
    if self.__handle_unsaved_changes():
      # stop the jack thread when exiting
      self.__config.save_config()
    if self.__midi_player:
        self.__midi_player.shutdown()
    Gtk.main_quit()

  def __set_song_bar_count(self, bar_count):
    #self.__spinbutton1.set_text(str(bar_count))
    self.__chord_sheet.set_song_bar_count(bar_count)

  def __compile_song(self, show_error):
    logging.debug("COMPILE_SONG")
    res = self.__song.compile_song()
    if show_error:
      if res == 0:
        """"""
        #self.__source_editor.put_error_mark_to(-1)
      elif res > 0 or res == -1:
        self.__show_mma_error(res)
    return res

  def __enable_pause_button(self):
    if self.uimanager.get_widget('/Toolbar/Pause').get_active():
    #if self.__toolbutton3.get_active():
      Gui.__ignore_toggle = True
      #self.__toolbutton3.set_active(False)
      self.uimanager.get_widget('/Toolbar/Pause').set_active(False)

  class ChordSheet(Gtk.DrawingArea):
    __bar_height = 40
    __cell_padding = 2
    __max_bar_chords_font = 40
    __bars_per_line = 4
    __color_no_song = "honeydew3"
    __color_playhead = "black"
    __color_selection = "SteelBlue"
    __color_cursor = "yellow"
    __color_events = "grey73"
    __color_song = "honeydew2"
    def __init__(self, song, config):
      Gtk.DrawingArea.__init__(self)
      self.set_size_request(1000,600)
      self.has_focus = True
      self.can_focus = True
      self.add_events(Gdk.EventMask.BUTTON1_MOTION_MASK | Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.KEY_PRESS_MASK | Gdk.EventMask.STRUCTURE_MASK)
      self.__song = song
      self.__config = config
      self.__playhead_pos = -1
      self.__selection_start = None
      self.__selection = set([])
      self.__clipboard = []
      self.__cursor_pos = 0
      self.__end_position = 0
      self.__drawing_area_width, self.__drawing_area_height = self.get_size_request()
      self.__bar_width = self.__drawing_area_width / self.__song.get_data().get_beats_per_bar()
      self.__bar_chords_width = self.__bar_width * 9 / 10
      self.__bar_info_width = self.__bar_width - self.__bar_chords_width
      self.surface = None
      self.connect("draw", self.on_draw)
      self.connect("realize", self.on_realize)
      self.connect("configure-event", self.on_configure)
      self.connect("key-press-event", self.on_key_press)
      self.connect("motion-notify-event", self.on_motion_notify)

    def move_playhead_to(self, pos):
      new_pos = pos * 2 + 1 if pos > -1 else -1
      old_pos = self.__playhead_pos
      if  old_pos != new_pos:
        self.__playhead_pos = new_pos
        self.__render_field(old_pos)
        self.__render_field(new_pos)

    def set_song_bar_count(self, bar_count):
        new_end = bar_count * 2
        maxlast = max(self.__end_position, new_end)
        fields_to_render = range(0, maxlast + 1)
        for field in fields_to_render: self.__render_field(field)
        self.__end_position = new_end
        if new_end == 0:
          self.__cursor_pos = 0
        elif self.__cursor_pos > new_end:
          self.__cursor_pos = new_end
        self.__move_cursor_to(self.__cursor_pos)
        self.__adjust_selection_bar_count_changed()

    def new_song_loaded(self):
      """ """
      self.__move_cursor_to(0) # cursor on field 0 => global buttons get refreshed
      self.__destroy_selection()

    def on_draw(self, widget, cr):
      cr.set_source_surface(self.surface, 0.0, 0.0)
      cr.paint()
      logging.debug('on_draw')
      return False

    def on_realize(self, widget):
      db = self.surface
      if db is not None:
        cc = cairo.Context(db)
        color = Gdk.color_parse(Gui.ChordSheet.__color_no_song)
        cc.set_source_rgb(color.red, color.green, color.blue)
        cc.rectangle(0, 0, self.__drawing_area_width, self.__drawing_area_height)
        logging.debug("width:%s" % self.__drawing_area_width)
        logging.debug("height:%s" % self.__drawing_area_height)
        cc.fill()
        db.flush()
      else:
        logging.debug('Invalid surface')
      logging.debug("on_realize")
      return True

    def on_configure(self, widget, event, data=None):
      """Configure the surface based on size of the widget"""
      if self.surface == None:
        allocation = widget.get_allocation()
        self.surface = widget.get_window().create_similar_surface(cairo.CONTENT_COLOR, allocation.width, allocation.height)
      print widget.get_allocated_width()
      print widget.get_allocated_height()
      logging.debug("on_configure")
      return False

    def on_key_press(self, widget, event):
      """ """
      key = event.keyval
      old_pos = self.__cursor_pos
      if key == Gdk.KEY_Left or key == Gdk.KEY_h or key == Gdk.KEY_H:
        targetPos = self.__cursor_pos - 1
        if targetPos >= 0:
          self.__move_cursor_to(targetPos)
      elif key == Gdk.KEY_Right or key == Gdk.KEY_l or key == Gdk.KEY_L:
        self.__move_cursor_to(self.__cursor_pos + 1)
      elif key == Gdk.KEY_Up or key == Gdk.KEY_k or key == Gdk.KEY_K:
        targetPos = self.__cursor_pos - ChordSheet.__bars_per_line * 2
        if targetPos >= 0:
          self.__move_cursor_to(targetPos)
      elif key == Gdk.KEY_Down or key == Gdk.KEY_j or key == Gdk.KEY_J:
        self.__move_cursor_to(self.__cursor_pos + ChordSheet.__bars_per_line * 2)
      elif key == Gdk.KEY_Home:
        self.__move_cursor_to(0)
      elif key == Gdk.KEY_End:
        self.__move_cursor_to(self.__end_position)
      elif event.get_state() & CONTROL_MASK and key == Gdk.KEY_Delete:
        self.cut_selection()
      elif event.get_state() & CONTROL_MASK and key == Gdk.KEY_Insert:
        self.copy_selection()
      elif event.get_state() & SHIFT_MASK and key == Gdk.KEY_Insert:
        self.paste_selection()
      elif key == Gdk.KEY_Delete:
        self.delete_selection()
      # move focus to chord entries
      elif self.__is_bar_chords(self.__cursor_pos):
        if key == Gdk.KEY_Return:
          self.__move_cursor_to(self.__cursor_pos + 2)
          self.__destroy_selection()
      # adjust selection
      if key in [ Gdk.KEY_Left, Gdk.KEY_Right, Gdk.KEY_Up, Gdk.KEY_Down, Gdk.KEY_Home, Gdk.KEY_End ]:
        if event.get_state() & SHIFT_MASK:
          self.__adjust_selection(old_pos)
        else:
          self.__destroy_selection()
      if key in [ Gdk.KEY_H, Gdk.KEY_L, Gdk.KEY_K, Gdk.KEY_J ]:
        self.__adjust_selection(old_pos)
      if key in [ Gdk.KEY_h, Gdk.KEY_l, Gdk.KEY_k, Gdk.KEY_j ]:
        self.__destroy_selection()
      # the event has been handled
      logging.debug('on_key_press')
      return True

    def on_motion_notify(self, widget, event):
      """ """
      if self.surface == None:
        return False
      (window, x, y, state)= event.window.get_pointer()
      # selection by mouse
      if state & Gdk.ModifierType.BUTTON1_MASK:
        pos = self.__locate_mouse_click(x, y)
        old_pos = self.__cursor_pos
        if not pos == old_pos:
          self.__move_cursor_to(pos)
          self.__adjust_selection(old_pos)
      logging.debug('on_motion_notify')
      return True

    def __render_field(self, field_num, chords=None):
      cursor = self.__cursor_pos == field_num
      playhead = self.__playhead_pos == field_num
      selection = field_num in self.__selection
      field_x = self.__get_pos_x(field_num)
      field_y = self.__get_pos_y(field_num)
      bar_num = field_num / 2
      if self.__is_bar_chords(field_num):
        if chords == None and bar_num < self.__song.get_data().get_bar_count():
          chords = self.__song.get_data().get_bar_chords(bar_num).get_chords()
        self.__render_chords_xy(bar_num, chords, field_x, field_y, playhead, cursor, selection)
      else:
        bar_info = None
        if bar_num <= self.__song.get_data().get_bar_count():
          bar_info = self.__song.get_data().get_bar_info(bar_num)
        chord_num = None
        if bar_num < self.__song.get_data().get_bar_count():
          chord_num = self.__song.get_data().get_bar_chords(bar_num).get_number()
        self.__render_bar_info_xy(bar_num, chord_num, bar_info, field_x, field_y, cursor, selection)
        
    def __render_chords_xy(self, bar_num, chords, bar_x, bar_y, playhead, cursor, selection):
      if bar_num >= self.__song.get_data().get_bar_count():
        color_code = Gui.ChordSheet.__color_no_song
      elif playhead:
        color_code = Gui.ChordSheet.__color_playhead
      elif selection:
        color_code = Gui.ChordSheet.__color_selection
      elif cursor:
        color_code = Gui.ChordSheet.__color_cursor
      else:
        color_code = Gui.ChordSheet.__color_song
      db = self.surface
      if db is not None:
        color = Gdk.color_parse(color_code)
        cc = cairo.Context(db)
        cc.set_source_rgb(color.red, color.green, color.blue)
        cc.rectangle(bar_x, bar_y, self.__bar_chords_width, Gui.ChordSheet.__bar_height)
        cc.fill()
        if cursor:
          color = Gdk.color_parse('black')
          cc.set_source_rgb(color.red, color.green, color.blue)
          cc.rectangle(bar_x, bar_y, self.__bar_chords_width - 1, Gui.ChordSheet.__bar_height - 1)
          cc.stroke()
        db.flush()
        if not chords:
          return
        if playhead:
          color = Gdk.color_parse('white')
        else:
          color = Gdk.color_parse('black')
        cc.set_source_rgb(color.red, color.green, color.blue)
        bar_chords_width = self.__bar_chords_width - (self.__song.get_data().get_beats_per_bar()) * Gui.ChordSheet.__cell_padding
        bar_chords_height = Gui.ChordSheet.__bar_height - 2 * Gui.ChordSheet.__cell_padding
        chord_width = bar_chords_width / self.__song.get_data().get_beats_per_bar()
        i = 0
        while i < len(chords):
          if chords[i][0] == '/':
            i = i +1
            continue
          if i % 2 == 0 and i + 1 < self.__song.get_data().get_beats_per_bar() and (i + 1 >= len(chords) or chords[i + 1][0] == '/' or chords[i + 1][0] == ''):
            self.__render_chord_xy(chords[i][0],
                          bar_x + (chord_width + Gui.ChordSheet.__cell_padding) * i,
                          bar_y + Gui.ChordSheet.__cell_padding,
                          chord_width + Gui.ChordSheet.__cell_padding + chord_width,
                          bar_chords_height,
                          playhead)
          else:
            self.__render_chord_xy(chords[i][0],
                          bar_x + (chord_width + Gui.ChordSheet.__cell_padding) * i,
                          bar_y + Gui.ChordSheet.__cell_padding,
                          chord_width,
                          bar_chords_height,
                          playhead)
          i = i + 1
      else:
        logging.debug('Invalid surface')

    def __get_pos_x(self, pos):
      return (pos / 2 % Gui.ChordSheet.__bars_per_line) * self.__bar_width \
                                        + (pos % 2 * self.__bar_info_width)
    def __get_pos_y(self, pos):
      return (pos / 2 / Gui.ChordSheet.__bars_per_line) * self.__bar_height

    def __is_bar_chords(self, field_num):
      return field_num % 2 == 1

    def __render_bar_info_xy(self, bar_num, chord_num, bar_info, x, y, cursor, selection):
      if bar_num > self.__song.get_data().get_bar_count():
        color_code = Gui.ChordSheet.__color_no_song
      elif selection:
        color_code = Gui.ChordSheet.__color_selection
      elif cursor:
        color_code = Gui.ChordSheet.__color_cursor
      elif bar_info.has_events():
        color_code = Gui.ChordSheet.__color_events
      else:
        color_code = Gui.ChordSheet.__color_song
      db = self.surface
      if db is not None:
        cc = cairo.Context(db)
        color = Gdk.color_parse(color_code)
        cc.set_source_rgb(color.red, color.green, color.blue)
        cc.rectangle(x, y, self.__bar_info_width, Gui.ChordSheet.__bar_height)
        cc.fill()
        if cursor:
          color = Gdk.color_parse('black')
          cc.set_source_rgb(color.red, color.green, color.blue)
          cc.rectangle(x, y, self.__bar_info_width - 1, Gui.ChordSheet.__bar_height -1)
        color = Gdk.color_parse('black')
        cc.set_source_rgb(color.red, color.green, color.blue)
        repeat_begin = bar_info.has_repeat_begin() if bar_info else False
        repeat_end = bar_info.has_repeat_end() if bar_info else False
        if repeat_begin or repeat_end: # draw repetitions
          if repeat_begin: self.__draw_repetition(x, y, False)
          if repeat_end: self.__draw_repetition(x, y, True)
        else:
          if bar_num < self.__song.get_data().get_bar_count() and chord_num: # draw bar number
            pango_layout = PangoCairo.create_layout(cc)
            pango_layout.set_text(str(chord_num), -1)
            fd = Pango.font_description_from_string('Monospace Bold 8')
            pango_layout.set_font_description(fd)
            ink, logical = pango_layout.get_pixel_extents()
            cc.move_to(x + Gui.ChordSheet.__cell_padding, y + (Gui.ChordSheet.__bar_height - ink.y - ink.height) - Gui.ChordSheet.__cell_padding)
            PangoCairo.update_layout(cc, pango_layout)
            PangoCairo.show_layout(cc, pango_layout)
        db.flush()
      else:
        logging.debug('Invalid surface')

    def __render_chord_xy(self, chord, x, y, width, height, playhead):
      """ Render one chord on position x,y. """
      db = self.surface
      if db is not None:
        cc = cairo.Context(db)
        if playhead: color = Gdk.color_parse('white')
        else: color = Gdk.color_parse('black')
        cc.set_source_rgb(color.red, color.green, color.blue)
        pango_layout = PangoCairo.create_layout(cc)
        pango_layout.set_text(chord, -1)
        fd = Pango.font_description_from_string(self.__config.get_chord_sheet_font())
        size = (Gui.ChordSheet.__max_bar_chords_font + 1) * Pango.SCALE
        while True:
          size = size - Pango.SCALE
          fd.set_size(size)
          pango_layout.set_font_description(fd)
          text_width, text_height = pango_layout.get_pixel_size()
          if text_width <= width and text_height <= height:
            break
        ink, logical = pango_layout.get_pixel_extents() #@UnusedVariable
        cc.move_to(x, y + (height - ink.y - ink.height))
        PangoCairo.update_layout(cc, pango_layout)
        PangoCairo.show_layout(cc, pango_layout)
        db.flush()
      else:
        logging.debug('Invalid surface')

    def __draw_repetition(self, x, y, end):
      db = self.surface
      if db is not None:
        cc = cairo.Context(db)
        # draw line
        middle_x = x + self.__bar_info_width / 2
        start_y = y + Gui.ChordSheet.__cell_padding
        width = Gui.ChordSheet.__cell_padding
        height = Gui.ChordSheet.__bar_height - 2 * Gui.ChordSheet.__cell_padding
        cc.rectangle(middle_x, start_y, width, height)
        cc.fill()
        # draw points
        point_size = Gui.ChordSheet.__cell_padding * 2
        upper_y = y + Gui.ChordSheet.__bar_height / 4
        lower_y = y + Gui.ChordSheet.__bar_height * 3 / 4 - point_size
        if end: x = x + self.__bar_info_width / 5
        else: x = x + self.__bar_info_width * 4 / 5 - point_size
        cc.arc(x, upper_y, point_size, 0, 360 * 64)
        cc.arc(x, lower_y, point_size, 0, 360 * 64)
        cc.fill()
        db.flush()
      else:
        logging.debug('Invalid surface')

    def __move_cursor_to(self, new_pos):
      old_pos = self.__cursor_pos
      self.__cursor_pos = new_pos
      self.__render_field(old_pos)
      if new_pos > self.__end_position:
        new_song_bar_count = new_pos / 2 + new_pos % 2
        self.__gui.change_song_bar_count(new_song_bar_count)
      self.__render_field(new_pos)
      #self.__gui.switch_bar(self.is_cursor_on_bar_chords())
      #self.__refresh_entries_and_events()
  
    def __adjust_selection_bar_count_changed(self):
      """ Number of bars has changed, maybe destroy the selection or shorten it. """
      if self.__selection_start == None:
        return
      elif self.__selection_start > self.__end_position:
        self.__destroy_selection()
      elif max(self.__selection) > self.__end_position:
        # remove all fields from selection which are out of song
        self.__selection = set([elem for elem in self.__selection if elem <= self.__end_position])

    def __destroy_selection(self):
      if self.__selection_start == None: return
      old_selection = self.__selection
      self.__selection_start = None
      self.__selection = set([])
      self.__redraw_selection(old_selection)
      
    def __locate_mouse_click(self, x, y):
      bar_x = 0
      bar_chords = 0
      u = self.__bar_info_width
      while x > u:
        if bar_chords == 0:
          u = u + self.__bar_chords_width
          bar_chords = 1
        else:
          u = u + self.__bar_info_width
          bar_x = bar_x + 1
          bar_chords = 0
      bar_y = 0
      u = Gui.ChordSheet.__bar_height
      while y > u:
        u = u + ChordSheet.__bar_height
        bar_y = bar_y + 1
      pos = self.__song.get_data().get_beats_per_bar() * 2 * bar_y + bar_x * 2 + bar_chords
      return pos

def main():
  GObject.threads_init()
  Glob.PACKAGE_VERSION = PACKAGE_VERSION
  #Glob.PACKAGE_BUGREPORT = PACKAGE_BUGREPORT
  #Glob.PACKAGE_URL = PACKAGE_URL
  #Glob.PACKAGE_TITLE = PACKAGE_TITLE
  #Glob.PACKAGE_COPYRIGHT = PACKAGE_COPYRIGHT
  Glob.LINE_MARKER = "%s/../resources/line-pointer.png" % PKG_DATA_DIR
  Glob.ERROR_MARKER = "%s/../resources/error-pointer.png" % PKG_DATA_DIR
  Glob.DEFAULT_CONFIG_FILE = "%s/../config/linuxband.rc" % PKG_DATA_DIR
  #Glob.GLADE = "%s/../glade/gui.ui" % PKG_DATA_DIR
  #Glob.LICENSE = "%s/../../../COPYING" % PKG_DATA_DIR
  Glob.PLAYER_PROGRAM = "%s/linuxband-player" % PKG_LIB_DIR
  # initialize logging
  console_log_level = logging.DEBUG
  Logger.initLogging(console_log_level)
  logging.debug("%s %s" % (PACKAGE_NAME, PACKAGE_VERSION))
  logging.debug("%s" % Glob.PLAYER_PROGRAM)
  app = Gui()
  Gtk.main()
  
if __name__ == "__main__":
  main()
