import sys
import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx
import configparser
import os
from maya import cmds
import inspect

pluginDir = os.path.dirname(inspect.getsourcefile(lambda: None))

sys.path.append(pluginDir + '/P4Library/') #Points Maya to the location of the P4 Library
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


def readP4Config():

    config = configparser.ConfigParser()
    config.read(pluginDir + '/config.txt')
    port = config['CONFIG']['port']
    user = config['CONFIG']['user']
    password = config['CONFIG']['password']
    client = config['CONFIG']['client']

    return port, user, password, client

port, user, password, client = readP4Config()
p4 = P4()                        
p4.port = port
p4.user = user
p4.password = password
p4.client = client            



def p4GetLatest():    
    if (not p4.connected()):
        p4.connect()
        p4.run_login()
    
    p4.run_sync()

def p4Submit():
    if (not p4.connected()):
        p4.connect()
        p4.run_login()

    maFile = cmds.file(q=True, sn=True)

    if (not maFile):
        print("File not saved, cannot push to perforce")
        return

    extra, relativeFilePath = maFile.split('/' + client + '/')

    print(relativeFilePath)




    change = p4.fetch_change()

    myFiles = ['//Animation_Production/' + relativeFilePath]
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
