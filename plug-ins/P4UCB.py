import sys
import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx
import maya.mel as mel
import os
from maya import cmds
import inspect
import configparser

sys.path.append('./P4Library/')  # Points Maya to the location of the P4 Library
from P4 import P4, P4Exception

INITIAL_CONFIG = {
    'port': '',
    'user': '',
    'password': '',
    'client': '',
}

pluginDir = os.path.dirname(inspect.getsourcefile(lambda: None))
callbacks = {}
callback_fns = []


def callback(event):
    """Decorator that registers a function as a callback, handling errors."""
    def f(func):
        def wrapped_func(*args):
            try:
                return func(*args)
            except Exception as e:
                cmds.confirmDialog(title='P4UCB Error', icon='critical',
                                   message=str(e), button=["ok"])
        callbacks[event] = wrapped_func
        return func
    return f


def readP4Config():
    config = configparser.ConfigParser()
    config.read(pluginDir + '/config.txt')
    return config['DEFAULT']


def p4_submit(*args):
    maFile = cmds.file(q=True, sn=True)

    if (not maFile):
        print("File not saved, cannot push to perforce")
        return

    config = readP4Config()

    extra, relativeFilePath = maFile.split('/' + config['client'] + '/')

    print(relativeFilePath)


    p4 = P4()                        # Create the P4 instance
    p4.port = config['port']
    p4.user = config['user']
    p4.password = config['password']
    p4.client = config['client']            # Set some environment variables

    p4.connect()
    p4.run_login()

    change = p4.fetch_change()

    myFiles = ['//Animation_Production/' + relativeFilePath]
    p4.run( "add", myFiles)
    change._description = "Test Automated Change"
    change._files = myFiles
    p4.run_submit( change )


def p4_setup(*args):
    """Display a window to allow changing Perforce config."""
    setup_window = cmds.window('Bugg Setup')
    cmds.rowColumnLayout()

    config = configparser.ConfigParser()
    config.read(pluginDir + '/config.txt')
    fields = {**INITIAL_CONFIG, **config['DEFAULT']}
    for field, initial in fields.items():
        cmds.textFieldGrp('textField_' + field, label=field + ': ', tx=initial)

    def save_config(*args):
        for field in fields:
            config['DEFAULT'][field] = cmds.textFieldGrp('textField_' + field, query=True, text=True)
        with open(pluginDir + '/config.txt', 'w') as configfile:
            config.write(configfile)
        cmds.deleteUI(setup_window)

    cmds.button(label='Save', command=save_config)
    cmds.showWindow(setup_window)


@callback(OpenMaya.MSceneMessage.kBeforeOpen)
def open_callback(*args):
    """Callback when a file is being opened."""
    close_callback()  # Opening a file also closes the previously opened file
    filename = OpenMaya.MFileIO.beforeOpenFilename()

    if '.ma' in filename or '.mb' in filename:
        cmds.confirmDialog(message="You are opening {}".format(filename), button=["ok","cancel"])


@callback(OpenMaya.MSceneMessage.kMayaExiting)
@callback(OpenMaya.MSceneMessage.kBeforeNew)
def close_callback(*args):
    """Callback when a file is being closed."""
    filename = cmds.file(q=True, sceneName=True)
    if '.ma' in filename or '.mb' in filename:
        cmds.confirmDialog(message="You are closing {}".format(filename), button=["ok","cancel"])


# Initialize the script plug-in
def initializePlugin(mobject):
    """Load the plugin in Maya."""
    global custom_menu
    mplugin = OpenMayaMPx.MFnPlugin(mobject)

    for event, callback in callbacks.items():
        callback_fns.append(OpenMaya.MSceneMessage.addCallback(event, callback))

    custom_menu = cmds.menu('P4', parent=mel.eval("$retvalue = $gMainWindow;"))
    cmds.menuItem(label='Setup', command=p4_setup, parent=custom_menu)
    cmds.menuItem(label='Submit', command=p4_submit, parent=custom_menu)


# Uninitialize the script plug-in
def uninitializePlugin(mobject):
    """Remove the plugin from Maya."""
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    cmds.deleteUI(custom_menu)

    try:
        for fn in callback_fns:
            OpenMaya.MCommandMessage.removeCallback(fn)
    except RuntimeError as e:
        sys.stderr.write("Failed to unregister callbacks: %s\n" % e)
