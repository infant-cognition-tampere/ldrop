"""DropPygtkView-class."""

import os
import gtk
import utils
import pango
import glib
from ExperimentStatusView import ExperimentStatusView


class DPV:
    """A pygtk-view for drop controller."""

    def __init__(self, ctrl, savedir):
        """Constructor."""
        # view knows the controller function calls
        self.ctrl = ctrl
        self.ctrl.on("sensorcount_changed", self.on_sensors_changed)
        self.ctrl.on("log_update", self.on_log_update)
        self.ctrl.on("error", self.on_error)

        self.savedir = savedir

        # UI generation code
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect("destroy", self.destroy)
        self.window.connect("key_press_event", self.on_keypress)
        self.window.set_border_width(5)
        self.window.set_size_request(860, 600)

        self.addsensorbutton = gtk.Button("Add sensor")
        self.addsensorbutton.connect("clicked",
                                     self.on_addsensorbutton_clicked)

        # log list
        self.liststore_log = gtk.ListStore(str)
        self.treeview_log = gtk.TreeView(self.liststore_log)

        self.log_column = gtk.TreeViewColumn("Log")
        self.log_cell = gtk.CellRendererText()
        self.treeview_log.append_column(self.log_column)
        self.log_column.pack_start(self.log_cell, True)
        self.log_column.set_attributes(self.log_cell, text=0)

        # scrollable container
        self.scrol_tree_status = gtk.ScrolledWindow()
        self.scrol_tree_status.set_policy(gtk.POLICY_NEVER,
                                          gtk.POLICY_AUTOMATIC)
        self.scrol_tree_status.add(self.treeview_log)

        self.trackstatus = ExperimentStatusView(self)

        self.idlabel = gtk.Label("Participant id")
        self.continuebutton = gtk.Button(label="Continue")
        self.continuebutton.connect("clicked", self.on_continuebutton_clicked)

        self.id_entry = gtk.Entry()
        self.id_entry.set_width_chars(10)
        self.id_entry.connect("changed", self.on_id_changed)

        self.id_entryhbox = gtk.HBox(homogeneous=False, spacing=10)
        self.id_entryhbox.pack_start(self.idlabel, expand=False)
        self.id_entryhbox.pack_start(self.id_entry, expand=False)

        self.sensors_vbox = gtk.VBox(homogeneous=False)
        self.sensor_scrollable = gtk.ScrolledWindow()
        self.sensor_scrollable.set_policy(gtk.POLICY_NEVER,
                                          gtk.POLICY_AUTOMATIC)
        self.sensor_scrollable.add_with_viewport(self.sensors_vbox)

        self.sensors_label = gtk.Label()
        self.sensors_label.set_alignment(0.0, 0.5)
        self.sensors_label.set_markup("<b>Active sensors:</b>")

        self.sensors_vbox.pack_end(self.addsensorbutton, expand=False)

        self.trackstatus_label = gtk.Label()
        self.trackstatus_label.set_markup("<b>Observation display:</b>")
        self.trackstatus_label.set_alignment(0.0, 0.5)

        self.expstatus_label = gtk.Label()
        self.expstatus_label.set_markup("<b>Experiment log:</b>")
        self.expstatus_label.set_alignment(0.0, 0.5)

        self.vbox_exp = gtk.VBox(homogeneous=False, spacing=10)

        self.table = gtk.Table(2, 6)
        self.table.set_col_spacings(4)
        self.table.set_row_spacings(4)
        self.table.attach(self.trackstatus_label, 1, 2, 0, 1,
                          xoptions=gtk.FILL, yoptions=gtk.FILL)
        self.table.attach(self.vbox_exp, 0, 1, 1, 2)
        self.table.attach(self.trackstatus, 1, 2, 1, 2)
        self.table.attach(self.sensors_label, 0, 1, 0, 1, xoptions=gtk.FILL,
                          yoptions=gtk.FILL)
        self.table.attach(self.expstatus_label, 1, 2, 2, 3, xoptions=gtk.FILL,
                          yoptions=gtk.FILL)
        self.table.attach(self.scrol_tree_status, 1, 2, 3, 4)
        self.table.attach(self.sensor_scrollable, 0, 1, 1, 4)

        self.buttonbar = gtk.HButtonBox()
        self.buttonbar.set_border_width(0)
        self.buttonbar.set_spacing(3)
        self.buttonbar.set_layout(gtk.BUTTONBOX_END)
        self.buttonbar.set_size_request(400, -1)

        # define buttons and togglebuttons
        image = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PLAY, 4)
        self.playbutton = gtk.Button(label=None)
        self.playbutton.add(image)
        self.playbutton.connect("clicked", self.on_playbutton_clicked)
        self.playbutton.set_sensitive(False)

        image = gtk.image_new_from_stock(gtk.STOCK_MEDIA_STOP, 4)
        self.stopbutton = gtk.Button(label=None)
        self.stopbutton.add(image)
        self.stopbutton.connect("clicked", self.on_stopbutton_clicked)


        # set buttons to the buttonbar
        self.buttonbar.add(self.continuebutton)
        self.buttonbar.add(self.playbutton)
        self.buttonbar.add(self.stopbutton)

        self.table.attach(self.id_entryhbox, 0, 1, 4, 5, xoptions=gtk.FILL,
                          yoptions=gtk.FILL)
        self.table.attach(self.buttonbar, 1, 3, 4, 5, xoptions=gtk.FILL,
                          yoptions=gtk.FILL)

        self.window.add(self.table)
        self.window.show_all()


    def on_error(self, errormsg):
        """Callback for error-signal."""
        self.show_message_box("Error: " + errormsg, "Drop error",
                              ("Ok", gtk.RESPONSE_OK), [None], [None])


    def clear_log(self):
        """Callback for experiment_started-signal."""
        # clear information about previous experiments rounds
        self.liststore_status.clear()

    def focus_on_gui(self):
        # set the focus back to experiment controller (in case of a keypress..)
        self.window.present()

    def on_addsensorbutton_clicked(self, button):
        """Callback for addeeg-button."""
        self.show_plugin_finder()

    def add_sensor(self, rhandle):
        """Sensor addition involving gui creation."""
        device_id = rhandle.get_sensor_id()
        gui_elements = rhandle.get_control_elements()

        hvbox = gtk.VBox(homogeneous=False, spacing=1)
        name = gtk.Label(device_id)
        rmbutton = gtk.Button("Remove")
        rmbutton.connect("clicked", self.remove_sensor, device_id, hvbox)
        topbar = gtk.HBox(homogeneous=False, spacing=10)
        topbar.pack_start(name)
        topbar.pack_end(rmbutton)
        hvbox.pack_start(topbar, expand=False)

        # input additional gui-elements
        for ge in gui_elements:
            if ge["type"] == "button":
                newbutton = gtk.Button(ge["id"])
                newbutton.connect("clicked", self.sensor_button_callback,
                                  device_id, ge["id"])
                hvbox.pack_end(newbutton)

        self.sensors_vbox.pack_start(hvbox, expand=False)
        self.window.show_all()
        self.trackstatus.add_model(rhandle)

    def sensor_button_callback(self, button, device_id, button_id):
        """Callback for sensor_button pressed-signal."""
        self.ctrl.sensor_action(device_id, button_id)

    def remove_sensor(self, button, device_id, hvbox):
        """Callback for the remove_sensor button(s). Parameter:buttonhandle."""
        self.ctrl.remove_sensor(device_id)
        self.sensors_vbox.remove(hvbox)


    def on_keypress(self, widget, event):
        """Keypress callback-function."""
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname in ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9",
                       "F10", "F11", "F12"]:
            self.ctrl.on_keypress(keyname)

    def on_id_changed(self, widget):
        """Id-change callback-function."""
        self.ctrl.set_participant_id(widget.get_text())
        self.check_play_conditions()

    def on_gui_action(self, editable):
        """Callback for change in gui that affects exp start conditions."""
        self.check_play_conditions()

    def on_sensors_changed(self):
        """Callback for sensors_changed_signal."""
        self.check_play_conditions()
        return False

    def on_playbutton_clicked(self, button):
        """Start the experiment or continue paused one."""
        #debug = self.debugbutton.get_active()
        self.ctrl.play()

    def on_continuebutton_clicked(self, button):
        """Callback for continuebutton click."""
        self.ctrl.continue_experiment()

    def on_stopbutton_clicked(self, button):
        """Callback for stopbutton click."""
        self.ctrl.stop()

    def on_log_update(self, logentry):
        """Callback for trial completion during experiment."""
        # append status value to listview
        self.liststore_log.append([str(logentry)])

        # hop down to see the last value added
        adj = self.scrol_tree_status.get_vadjustment()
        adj.set_value(adj.upper-adj.page_size)

    def check_play_conditions(self):
        """Check all prequisities running experiment met. Activate buttons."""
        # participant id
        id_code = self.ctrl.get_participant_id()

        if id_code is not "": #\
               # and ((len(self.ctrl.get_sensors()) != 0) or debugmode):
            self.playbutton.set_sensitive(True)
        else:
            self.playbutton.set_sensitive(False)

    def destroy(self, widget, data=None):
        """Class destroyer callback."""
        gtk.main_quit()
        self.ctrl.close_gui()
        self.ctrl = None

    def main(self):
        """PyGTK application main loop or waiting function."""
        gtk.gdk.threads_init()
        gtk.main()

    def text_dialog(self, txt):
        """
        Spawn a dialog window with a possibility to put scrollable text.

        parameters:
        txt[list of strings], each string represents a row of in the dialog.
        """
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.set_size_request(400, 600)

        scrollable = gtk.ScrolledWindow()
        scrollable.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)

        textarena = gtk.TextView()
        textbuffer = textarena.get_buffer()

        # generate available tags
        textbuffer.create_tag("red", background="#ffcccc")
        textbuffer.create_tag("blue", background="#ccccff")
        textbuffer.create_tag("h1", size_points=14)
        textbuffer.create_tag("bold", weight=pango.WEIGHT_BOLD)
        textbuffer.create_tag("italic", style=pango.STYLE_ITALIC)

        while len(txt) > 0:
            # get the position of the iter (end)
            position = textbuffer.get_start_iter()

            txt_raw = txt.pop()
            if type(txt_raw) is list:
                # get the latest text-thing

                tag = txt_raw[0]
                text = " " + txt_raw[1] + '\n'

                # insert text with the tag
                textbuffer.insert_with_tags_by_name(position, text, tag)

            else:
                textbuffer.insert(position, " " + txt_raw + "\n")

        textarena.set_editable(False)
        textarena.set_cursor_visible(False)
        scrollable.add(textarena)
        window.add(scrollable)
        window.show_all()

    def show_message_box(self, message, title="", buttons=("OK",
                         gtk.RESPONSE_OK), follow_up=[None],
                         follow_up_args=[None]):
        """Create a message box with supplied information and callbacks."""
        def close_dialog(dlg, rid):
            dlg.destroy()

            if rid == -4:
                # was closed from x-button
                return False

            # what button pressed, what callback?
            responses = buttons[1::2]
            button_indice = responses.index(rid)

            fu = follow_up[button_indice]
            args = follow_up_args[button_indice]

            if fu is not None:
                if args is not None:
                    glib.idle_add(fu, args)
                else:
                    glib.idle_add(fu)

        parent = self.window
        dlg = gtk.Dialog(title, parent, 0, buttons)
        label = gtk.Label(message)
        dlg.vbox.pack_start(label)
        label.show()
        dlg.connect("response", close_dialog)

        # show the message box, waiting answer
        dlg.show()

    def show_plugin_finder(self):
        """A mini-GUI that shows a list of plugings for user to select from."""
        def on_plugin_finder_select(widget, rid, htreeview, callback):
            """Callback for plugin_finder_select-button."""
            plugin = utils.tree_get_first_column_value(htreeview)
            widget.destroy()

            # if pressed select
            if rid == -5:
                if plugin is None:
                    return
                glib.idle_add(callback, plugin)

        dlg = gtk.Dialog("Plugin browser", self.window, 0, ("Select",
                                                            gtk.RESPONSE_OK))
        dlg.set_border_width(5)
        dlg.set_size_request(300, 480)
        dlg.set_destroy_with_parent(True)

        pliststore = gtk.ListStore(str, str)
        treeview = gtk.TreeView(pliststore)

        # create the name-column
        plugin_column = gtk.TreeViewColumn("Name")
        plugin_cell = gtk.CellRendererText()
        treeview.append_column(plugin_column)
        plugin_column.pack_start(plugin_cell, True)
        plugin_column.set_attributes(plugin_cell, text=0)

        # create description-column
        description_column = gtk.TreeViewColumn("Description")
        description_cell = gtk.CellRendererText()
        treeview.append_column(description_column)
        description_column.pack_start(description_cell, True)
        description_column.set_attributes(description_cell, text=1)

        treeview_label = gtk.Label()
        treeview_label.set_alignment(0.0, 0.5)
        treeview_label.set_markup("<b>Select plugin:</b>")

        dlg.vbox.set_homogeneous(False)
        dlg.vbox.pack_start(treeview_label, expand=False)
        dlg.vbox.pack_start(treeview)
        dlg.show_all()
        dlg.connect("response", on_plugin_finder_select, treeview,
                    self.ctrl.addsensor)

        # add plugins to liststore
        plugins = self.ctrl.pluginmanager.getAllPlugins()
        for p in plugins:
            pliststore.append([p.name, p.description])
