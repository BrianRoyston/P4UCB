# P4UCB
This plug-in was originally developed by Brian Royston and Ryan Adolf for use in the production of an animated short film with other students at UC Berkeley. 
It was originally made for this use case primarily, so other use cases may require some tweaking. If your whole team is on Windows, there is an official plug-in called 
P4GT, but it is only available on Windows, hence why we made this.

# Setup
1) Make sure you have Perforce (https://www.perforce.com/downloads/helix-visual-client-p4v)
2) Clone this repository, or Download Zip.
3) Navigate to your Maya folder:
   - Windows: C:/Users/<username>/Documents/maya/<version>
   - Mac: /Users/<username>/Library/Preferences/Autodesk/maya/<version>
 4) Copy the folder labeled plug-ins into the maya/<version>/ directory.
 5) Now when you open Maya you should see P4UCB as an option under Windows -> Settings/Preferences -> Plug-in Manager
 6) Load the plug-in
    - If you’re using a Mac, you’ll see a dialog saying that the perforce library is from an unrecognized developer and the plugin will not load. To fix this, open System Preferences and click “Security and Privacy”
    - Click the “General” tab.
    - Click the unlock button on the bottom and approve the library to load.
    - Quit and reopen Maya
    - Load the plugin again

7) That should add a “P4” tab at the top of maya
8) Go to P4->Setup Plugin
9) Enter your perforce info in the popup
10) Save this and restart Maya (just to be safe)
11) Now you should be fully setup. 

# How to Use
- Make sure you have your project set to a folder inside the perforce workspace. 
- It should automatically try to sync whenever you open a file, but you can do it yourself with P4 -> sync
- Whenever you save a new file inside of the project folder, it should prompt you if you want to add it to perforce. (You can do this manually with P4->Add To Perforce)
- Likewise whenever you open an existing file it will ask if you want to check it out (P4 -> Start Editing)
  - You cannot modify a file without checking it out, Maya will yell at you that it is read only
  - As soon as one person checks out a file it will block everyone else from modifying that file to avoid conflicts.
  
- Once you are done you need to submit your changes with a quick description. (should automatically prompt you when you close the file but you can do it manually with P4 -> Submit)
- If you want to throw out any changes you have made to a file from the current live version you can Revert it
- Every file that is checked out, must be Submitted or Reverted, otherwise it stays locked and other people can’t edit it.

