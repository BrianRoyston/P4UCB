import sys
import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx
import os
from maya import cmds
import maya.OpenMaya as api

kPluginCmdName = "p4UCB_Submit"

# Command
class scriptedCommand(OpenMayaMPx.MPxCommand):
    def __init__(self):
        OpenMayaMPx.MPxCommand.__init__(self)

    # Invoked when the command is run.
    def doIt(self,argList):
        p4Submit()

def p4Submit():
    print('hello world')



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
