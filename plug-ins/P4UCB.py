import sys
import configparser
import os
import inspect
import ssl
from io import BytesIO
from zipfile import ZipFile
from urllib.request import urlopen
import tempfile
from distutils.dir_util import copy_tree

import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx
import maya.mel as mel
from maya import cmds

pluginDir = os.path.dirname(inspect.getsourcefile(lambda: None))

sys.path.append(pluginDir + '/P4Library/') #Points Maya to the location of the P4 Library
from P4 import P4,P4Exception

ARCHIVE_URL = 'https://github.com/BrianRoyston/P4UCB/archive/refs/heads/main.zip'
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

def isFileOpened(filepath):
    openedFiles = p4.run("opened")
    for fileInfo in openedFiles:
        if (fileInfo['depotFile'] == filepath): 
            return True
    return False

def getOpenedList():
    openedFiles = p4.run("opened")
    return list(map(lambda fileInfo : fileInfo['depotFile'], openedFiles))

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
        print("Warning: File not saved, cannot check perforce")
        return None

    if (('/' + config['client'] + '/') not in maFile):
        print("Warning: Workspace (" + config['client'] + ") was not found in file path")
        return None
    extra, relativeFilePathLocal = maFile.split('/' + config['client'] + '/')
    return '//Animation_Production/' + relativeFilePathLocal


def p4GetLatest(*args, verbose=True):
    print("p4GetLatest")
    connectToP4()
    filepath = getRelativeFilePath()
    try:
        changedFiles = p4.run_sync()
        """for fileInfo in changedFiles:
            if (fileInfo['depotFile'] == filepath): 
                reloadResponse = cmds.confirmDialog(title='Reload?', message='The current file was just updated with the last sync, would you like to re-open it?', button=["Yes", "No"])
                if reloadResponse == "Yes":
                    mel.eval("fopen " + cmds.file(q=True, sn=True))
                return"""
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

    openedResult = p4.run("opened","-a", relativeFilePath)
    for fileInfo in openedResult:
        if 'ourLock' in fileInfo.keys():
            cmds.confirmDialog(title='File Locked', icon='critical',
                                   message='This file is currently checked out and locked by: {}'.format(fileInfo['user']), button=["ok"])
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

    openedFiles = getOpenedList()

    def submitFiles(*args):
        selectedFiles = []
        for i in range(len(openedFiles)):
            if (cmds.checkBox("cb" + str(i), query=True, value=True)):
                selectedFiles.append(openedFiles[i])
        cmds.layoutDialog( dismiss="Continue")

        if (len(selectedFiles) <= 0):
            return # no files selected, nothing to submit

        result = cmds.promptDialog(title='Submit Changes', message="Enter a change description",
                                  button=['Cancel', 'Submit'])
        if result == 'Submit':
            inputDescription = cmds.promptDialog(query=True, text=True) or "Blank Description"
            change = p4.fetch_change()

            myFiles = selectedFiles
            change._description = inputDescription
            change._files = myFiles
            p4.run_submit( change )

    def checkboxPrompt():
        # Get the dialog's formLayout.
        #
        form = cmds.setParent(q=True)

        # layoutDialog's are not resizable, so hard code a size here,
        # to make sure all UI elements are visible.
        #
        cmds.formLayout(form, e=True, width=300)

        t = cmds.text(l='Files To Submit')

        spacer = 5
        top = 5
        edge = 5

        # What the actual fuck is this UI system...
        attachForm = [(t, 'top', top), (t, 'left', edge), (t, 'right', edge)]
        attachNone = [(t, 'bottom')]
        attachControl = []
        attachPosition = []

        above = t

        checkBoxes = []
        count = 0
        for file in openedFiles:
            cb = cmds.checkBox("cb" + str(count), label = file, value = True)
            checkBoxes.append(cb)

            attachControl.append((cb, 'top', spacer, above))
            attachForm.append((cb, 'left', edge))
            attachForm.append((cb, 'right', edge))
            attachNone.append((cb, 'bottom'))

            above = cb
            count += 1
        

        b1 = cmds.button(label='Cancel', c='cmds.layoutDialog( dismiss="Cancel")')
        b2 = cmds.button(label='Continue', c=submitFiles)

        attachForm.append((b1, 'left', edge))
        attachForm.append((b2, 'right', edge))
        attachForm.append((b1, 'bottom', edge))
        attachForm.append((b2, 'bottom', edge))

        attachControl.append((b1, 'top', spacer, above))
        attachControl.append((b2, 'top', spacer, above))

        attachPosition.append((b1, 'right', spacer, 50))
        attachPosition.append((b2, 'left', spacer, 50))


        cmds.formLayout(form, edit=True,
                    attachForm = attachForm,
                    attachNone = attachNone,
                    attachControl = attachControl,
                    attachPosition = attachPosition)


    cmds.layoutDialog(ui=checkboxPrompt)


def p4Revert(*args, filepathOverride = None):
    print("p4Revert")

    filename = cmds.file(q=True, sceneName=True)
    confirmResponse = cmds.confirmDialog(title='Are you sure?', message="Are you sure you want to revert all local changes made to {}?".format(filename), button=["Revert","No"])
    if (confirmResponse != "Revert"):
        return

    connectToP4()

    relativeFilePath = filepathOverride
    if not relativeFilePath: #filepath override is None
        relativeFilePath = getRelativeFilePath()

    if (not relativeFilePath): #invalid file, skip
        return

    myFiles = [relativeFilePath]
    p4.run("revert", myFiles)

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

def p4Update(*args):
    """Update the plug-in from GitHub."""
    resp = urlopen(ARCHIVE_URL, context=ssl.SSLContext())
    myzip = ZipFile(BytesIO(resp.read()))

    with tempfile.TemporaryDirectory() as tmpdirname:
        myzip.extractall(tmpdirname)
        copy_tree(tmpdirname + '/P4UCB-main/plug-ins', pluginDir)

@callback(OpenMaya.MSceneMessage.kAfterSave)
def save_callback(*args):
    """Callback right after a file is saved"""
    filepath = getRelativeFilePath()
    if (not filepath): #Filepath isn't in directory, ignore
        return
    connectToP4()

    try:
        fileInfo = p4.run( "files",  filepath)

        #file could still have been deleted in the past
        if fileInfo[0]['action'] == 'delete':
            addResponse = cmds.confirmDialog(message="The file you saved: {}, was not found in Perforce, would you like to add it.".format(filepath), button=["add", "cancel"])
            if (addResponse == 'add'):
                p4Add(None)
    except P4Exception:
        #File check failed, means file isn't in perforce
        if (isFileOpened(filepath)):#file already opened no need to prompt
            return
        addResponse = cmds.confirmDialog(message="The file you saved: {}, was not found in Perforce, would you like to add it.".format(filepath), button=["add", "cancel"])
        if (addResponse == 'add'):
            p4Add(None)

@callback(OpenMaya.MSceneMessage.kAfterNew)
def afterNew_callback(*args):
    """Callback after a new file is made"""
    connectToP4()
    try:
        p4GetLatest(verbose=False) #Sync
        print("Synced")
    except P4Exception:
        print("Already Synced")

    openedFiles = getOpenedList()
    if (len(openedFiles) > 0):
        openedResponse = cmds.confirmDialog(title='Checked out files', message="The following files are still checkout out. What would you like to do? \n{}".format(openedFiles), button=["Submit All", "Revert All", "Ask me later"])
        if openedResponse == "Submit All":
            p4Submit(None)      
        elif openedResponse == "Revert All":
            for filepath in openedFiles:
                p4Revert(None, filepathOverride=filepath)

@callback(OpenMaya.MSceneMessage.kAfterOpen)
def afterOpen_callback(*args):
    """Callback after a file is opened"""
    
    afterNew_callback()

    filepath = getRelativeFilePath()
    if (not filepath): #Filepath isn't in directory, ignore
        return
    try:
        fileInfo = p4.run( "files", filepath)
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

    if isFileOpened(filepath):
        filename = cmds.file(q=True, sceneName=True)
        submitResponse = cmds.confirmDialog(title='Submit Changes?', message="{} is still checkout out, would you like to submit it or revert your changes?".format(filename), button=["Submit","Revert"])
        if (submitResponse == "Submit"):
            p4Submit(None)
        if (submitResponse == "Revert"):
            p4Revert(None)



# Initialize the script plug-in
def initializePlugin(mobject):
    """Load the plugin in Maya."""
    global custom_menu
    for event, callback in callbacks.items():
        callback_fns.append(OpenMaya.MSceneMessage.addCallback(event, callback))

    custom_menu = cmds.menu('P4', parent=mel.eval("$retvalue = $gMainWindow;"))
    cmds.menuItem(label='Setup Plugin', command=p4Setup, parent=custom_menu)
    cmds.menuItem(label='Update Plugin', command=p4Update, parent=custom_menu)
    cmds.menuItem(divider=True)
    cmds.menuItem(label='Sync', command=p4GetLatest, parent=custom_menu)
    cmds.menuItem(label='Add To Perforce', command=p4Add, parent=custom_menu)
    cmds.menuItem(label='Start Editing', command=p4Checkout, parent=custom_menu)
    cmds.menuItem(label='Revert', command=p4Revert, parent=custom_menu)
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
