import sys
import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx
import maya.mel as mel
import os
from maya import cmds
import inspect
import configparser

sys.path.append('./P4Library/') #Points Maya to the location of the P4 Library
from P4 import P4,P4Exception

#command name that will be added to maya.cmds.
kPluginCmdName = "p4_Submit"

INITIAL_CONFIG = {
    'port': '',
    'user': '',
    'password': '',
    'client': '',
}

# Command
class scriptedCommand(OpenMayaMPx.MPxCommand):
    def __init__(self):
        OpenMayaMPx.MPxCommand.__init__(self)

    # Invoked when the command is run.
    def doIt(self,argList):
        p4Submit()

pluginDir = os.path.dirname(inspect.getsourcefile(lambda: None))

def readP4Config():
    config = configparser.ConfigParser()
    config.read(pluginDir + '/config.txt')
    return config['DEFAULT']

def p4Submit():
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

def setup(*args):
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

# Creator
def cmdCreator():
    return OpenMayaMPx.asMPxPtr( scriptedCommand() )

# Initialize the script plug-in
def initializePlugin(mobject):
    global saveCallback, customMenu
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    try:
        mplugin.registerCommand( kPluginCmdName, cmdCreator )
    except:
        sys.stderr.write( "Failed to register command: %s\n" % kPluginCmdName )
        raise
    saveCallback = OpenMaya.MSceneMessage.addCallback(
        OpenMaya.MSceneMessage.kAfterSave,
        saveCallbackFunc)

    customMenu = cmds.menu('P4', parent=mel.eval("$retvalue = $gMainWindow;"))
    cmds.menuItem(label='Setup', command=setup, parent=customMenu)
    cmds.menuItem(label='Submit', command='cmds.p4_Submit()', parent=customMenu)


# Uninitialize the script plug-in
def uninitializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    cmds.deleteUI(customMenu)
    try:
        mplugin.deregisterCommand( kPluginCmdName )
    except:
        sys.stderr.write( "Failed to unregister command: %s\n" % kPluginCmdName )
    try:
        OpenMaya.MCommandMessage.removeCallback(saveCallback)
    except RuntimeError as e:
        print(e)

def saveCallbackFunc(*args):
    try:
        fileName = cmds.file(q=True, sceneName=True)

        if '.ma' in fileName or '.mb' in fileName:
            cmds.confirmDialog(message="You saved {}".format(fileName), button=["ok","cancel"])
    except Exception as e:
        # Print in case I made an oopsie
        print(e)
