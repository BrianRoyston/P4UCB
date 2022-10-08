import sys
import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx
import os
from maya import cmds
import inspect

sys.path.append('./P4Library/') #Points Maya to the location of the P4 Library
from P4 import P4,P4Exception 

import maya.OpenMaya as api

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
    f = open(pluginDir + '/config.txt', 'r')
    lines = f.readlines()
    port = ''
    user = ''
    password = ''
    client = ''
    for line in lines:
        key, value = line.split('=')
        key = key.strip()
        value = value.strip()
        if key == 'port':
            port = value
        elif key == 'user':
            user = value
        elif key == 'password':
            password = value
        elif key == 'client':
            client = value

    return port, user, password, client


def p4Submit():
    maFile = cmds.file(q=True, sn=True)

    if (not maFile):
        print("File not saved, cannot push to perforce")
        return

    port, user, password, client = readP4Config()

    extra, relativeFilePath = maFile.split('/' + client + '/')

    print(relativeFilePath)


    p4 = P4()                        # Create the P4 instance
    p4.port = port
    p4.user = user
    p4.password = password
    p4.client = client            # Set some environment variables

    p4.connect()
    p4.run_login()

    change = p4.fetch_change()

    myFiles = ['//' + relativeFilePath]
    p4.run( "add", myFiles)
    change._description = "Test Automated Change"
    change._files = myFiles 
    p4.run_submit( change )


    


# Creator
def cmdCreator():
    return OpenMayaMPx.asMPxPtr( scriptedCommand() )

# Initialize the script plug-in
def initializePlugin(mobject):
    global saveCallback
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    try:
        mplugin.registerCommand( kPluginCmdName, cmdCreator )
    except:
        sys.stderr.write( "Failed to register command: %s\n" % kPluginCmdName )
        raise
    saveCallback = api.MSceneMessage.addCallback(
        api.MSceneMessage.kAfterSave,
        saveCallbackFunc)


# Uninitialize the script plug-in
def uninitializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    try:
        mplugin.deregisterCommand( kPluginCmdName )
    except:
        sys.stderr.write( "Failed to unregister command: %s\n" % kPluginCmdName )
    try:
        api.MCommandMessage.removeCallback(saveCallback)
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
