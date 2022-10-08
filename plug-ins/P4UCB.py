import sys
import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx
import configparser
import maya.mel as mel
import os
from maya import cmds
import inspect
import configparser

pluginDir = os.path.dirname(inspect.getsourcefile(lambda: None))

sys.path.append(pluginDir + '/P4Library/') #Points Maya to the location of the P4 Library
from P4 import P4,P4Exception

import maya.OpenMaya as api


INITIAL_CONFIG = {
    'port': '',
    'user': '',
    'password': '',
    'client': '',
}


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
    configParser = configparser.ConfigParser()
    configParser.read(pluginDir + '/config.txt')

    return configParser['DEFAULT']

config = readP4Config()
p4 = P4()

def connectToP4():
    if (not p4.connected()):
        config = readP4Config()
        p4.port = config['port']
        p4.user = config['user']
        p4.password = config['password']
        p4.client = config['client']
        try:
            p4.connect()
            p4.run_login()
        except Exception as e:
            cmds.confirmDialog(title='Cannot Connect to P4', icon='critical',
                               message=str(e), button=["ok"])
            raise e


def getRelativeFilePath():
    maFile = cmds.file(q=True, sn=True)
    if (not maFile):
        print("Warning: File not saved, cannot push to perforce")
        return None

    if (('/' + config['client'] + '/') not in maFile):
        print("Warning: Workspace (" + config['client'] + ") was not found in file path")
        return None
    extra, relativeFilePathLocal = maFile.split('/' + config['client'] + '/')
    return '//Animation_Production/' + relativeFilePathLocal


def p4GetLatest(*args, verbose=True):
    print("p4GetLatest")
    connectToP4()

    try:
        p4.run_sync()
    except Exception as e:
        if 'up-to-date' in str(e):
            if verbose:
                cmds.confirmDialog(title='Succcessfully synced',
                                   message='Files are already up to date', button=["ok"])
        else:
            cmds.confirmDialog(title='Error Syncing', icon='critical',
                               message=str(e), button=["ok"])

def p4Checkout(*args):
    print("p4Checkout")
    connectToP4()

    relativeFilePath = getRelativeFilePath()
    if (not relativeFilePath): #invalid file, skip
        return

    myFiles = [relativeFilePath]
    p4.run( "edit", myFiles)
    p4.run( "lock", myFiles )

def p4Add(*args):
    print("p4Add")
    connectToP4()

    relativeFilePath = getRelativeFilePath()
    if (not relativeFilePath): #invalid file, skip
        return

    myFiles = [relativeFilePath]
    p4.run( "add", myFiles)

def p4Submit(*args):
    print("p4Submit")
    connectToP4()

    relativeFilePath = getRelativeFilePath()
    if (not relativeFilePath): #invalid file, skip
        return

    inputDescription = cmds.promptDialog(message="Enter a change description")
    if (not inputDescription):
        inputDescription = "Blank Description"
    change = p4.fetch_change()

    myFiles = [relativeFilePath]
    change._description = inputDescription
    change._files = myFiles
    p4.run_submit( change )

def p4Setup(*args):
    """Display a window to allow changing Perforce config."""
    global config
    print("p4Setup")

    setup_window = cmds.window('Bugg Setup')
    cmds.rowColumnLayout()

    configParser = configparser.ConfigParser()
    configParser.read(pluginDir + '/config.txt')
    fields = {**INITIAL_CONFIG, **configParser['DEFAULT']}
    for field, initial in fields.items():
        cmds.textFieldGrp('textField_' + field, label=field + ': ', tx=initial)

    def save_config(*args):
        for field in fields:
            configParser['DEFAULT'][field] = cmds.textFieldGrp('textField_' + field, query=True, text=True)
        with open(pluginDir + '/config.txt', 'w') as configfile:
            configParser.write(configfile)
        cmds.deleteUI(setup_window)

    cmds.button(label='Save', command=save_config)
    cmds.showWindow(setup_window)

    #reset config values with new file
    p4.disconnect()
    config = readP4Config()


@callback(OpenMaya.MSceneMessage.kAfterSave)
def save_callback(*args):
    """Callback right after a file is saved"""
    filepath = getRelativeFilePath()
    if (not filepath): #Filepath isn't in directory, ignore
        return
    connectToP4()
    try:
        p4.run( "files",  filepath)
    except P4Exception:
        #File check failed, means file isn't in perforce
        addResponse = cmds.confirmDialog(message="The file you saved: {}, was not found in Perforce, would you like to add it.".format(filepath), button=["add", "cancel"])
        if (addResponse == 'add'):
            p4Add(None)

@callback(OpenMaya.MSceneMessage.kAfterOpen)
def afterOpen_callback(*args):
    """Callback after a file is opened"""
    filepath = getRelativeFilePath()
    if (not filepath): #Filepath isn't in directory, ignore
        return
    connectToP4()

    try:
        p4GetLatest(verbose=False) #Sync
        print("Synced")
    except P4Exception:
        print("Already Synced")

    try:
        p4.run( "files",  filepath)
        #Didn't fail, file already in perforce, ask to edit
        editResponse = cmds.confirmDialog(title='Check out?', message="Would you like to check out this file for editing?", button=["Check Out", "Don't Check Out"])
        if (editResponse == "Check Out"):
            p4Checkout(None)

    except P4Exception:
        #File check failed, means file isn't in perforce
        addResponse = cmds.confirmDialog(title='Add?', message="This file: {}, was not found in Perforce, would you like to add it.".format(filepath), button=["Add", "Don't Add"])
        if (addResponse == "yes"):
            p4Add(None)


@callback(OpenMaya.MSceneMessage.kBeforeOpen)
def open_callback(*args):
    """Callback when a file is being opened."""
    close_callback()  # Opening a file also closes the previously opened file
    filename = OpenMaya.MFileIO.beforeOpenFilename()


@callback(OpenMaya.MSceneMessage.kMayaExiting)
@callback(OpenMaya.MSceneMessage.kBeforeNew)
def close_callback(*args):
    """Callback when a file is being closed."""

    filepath = getRelativeFilePath()
    if (not filepath): #Filepath isn't in directory, ignore
        return
    connectToP4()

    filename = cmds.file(q=True, sceneName=True)
    submitResponse = cmds.confirmDialog(title='Submit Changes?', message="Would you like to Submit any changes to {}?".format(filename), button=["Submit","Don't Submit"])
    if (submitResponse == "Submit"):
        p4Submit(None)


# Initialize the script plug-in
def initializePlugin(mobject):
    """Load the plugin in Maya."""
    global custom_menu
    for event, callback in callbacks.items():
        callback_fns.append(OpenMaya.MSceneMessage.addCallback(event, callback))

    custom_menu = cmds.menu('P4', parent=mel.eval("$retvalue = $gMainWindow;"))
    cmds.menuItem(label='Setup', command=p4Setup, parent=custom_menu)
    cmds.menuItem(label='Sync', command=p4GetLatest, parent=custom_menu)
    cmds.menuItem(label='Add To Perforce', command=p4Add, parent=custom_menu)
    cmds.menuItem(label='Start Editing', command=p4Checkout, parent=custom_menu)
    cmds.menuItem(label='Submit', command=p4Submit, parent=custom_menu)


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
