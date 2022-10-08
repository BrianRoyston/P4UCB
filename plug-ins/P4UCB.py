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

# Command
class scriptedCommand(OpenMayaMPx.MPxCommand):
    def __init__(self):
        OpenMayaMPx.MPxCommand.__init__(self)

    # Invoked when the command is run.
    def doIt(self,argList):
        p4Submit()

pluginDir = os.path.dirname(inspect.getsourcefile(lambda: None))

def readP4Config():
    return config.read(pluginDir + '/config.txt')['DEFAULT']

def p4Submit():
    maFile = cmds.file(q=True, sn=True)

    if (not maFile):
        print("File not saved, cannot push to perforce")
        return

    config = readP4Config()

    extra, relativeFilePath = maFile.split('/' + client + '/')

    print(relativeFilePath)


    p4 = P4()                        # Create the P4 instance
    p4.port = config['port']
    p4.user = config['user']
    p4.password = config['password']
    p4.client = config['client']            # Set some environment variables

    p4.connect()
    p4.run_login()

    change = p4.fetch_change()

    myFiles = ['//' + relativeFilePath]
    p4.run( "add", myFiles)
    change._description = "Test Automated Change"
    change._files = myFiles
    p4.run_submit( change )

def setup(_):
    global setup_window
    setup_window = cmds.window('Bugg Setup')
    cmds.rowColumnLayout()

    cmds.textFieldGrp('textField_A', label = 'Textfield A: ')
    cmds.textFieldGrp('textField_B', label = 'Textfeild B: ', tx='sample')

    cmds.button(label = 'Done', command = queryTextField)

    cmds.showWindow( setup_window )

def queryTextField(*args):

    text_A = cmds.textFieldGrp( 'textField_A', query = True, text = True)
    text_B = cmds.textFieldGrp( 'textField_B', query = True, text = True)

    print(text_A, text_B)
    cmds.deleteUI(setup_window)

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
    cmds.menuItem(label='Submit', command='cmds.p4UCB_Submit()', parent=customMenu)


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
