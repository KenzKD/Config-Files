# ColemakDH-Alternative-ANSI

I made an alternative version for the [ColemakDH site](https://colemakmods.github.io/mod-dh/) Layout on to suit my laptop keyboard.

I know that the curl/angle mod gets sacrificed here but this is the best compromise I could come up with for my laptop since some of my keycaps dont match with others.(I like my physical layout to match the software) 

I used the original [ColemakDH for matrix](https://github.com/ColemakMods/mod-dh/tree/master/klc) as a basis and then changed it a bit so that the :
* CAPSLOCK was mapped to be BACKSPACE 
* INSERT was mapped to be CAPSLOCK      (Since I have honestly never had to use this key for anything)
* Swapped places of ' and ;     (Just find it easier to use it like this)

## Windows
If you want to use this layout in Windows:

1) Download the [Colemaka.zip](https://github.com/KenzKD/ColemakDH-Alternative-ANSI/blob/main/colemaka.zip) file
2) Extract the file.
3) Open the extracted file and the open the colemaka folder inside it.
4) You should be seeing this now: 
    
    ![image](https://user-images.githubusercontent.com/65004578/145541153-979cd7cb-ce2a-479d-9eea-9b92f358426d.png)
5) Double-Click the Setup.exe file and a prompt will pop up about running 3rd party software.Click on more information and select Run Anyway.
6) From there just follow the instructions of the installer.
7) Once the install is done go to Settings -> Time and Language -> Language 
8) In Preferred Language there should already be English(United States). Click on it and then click on Options.
9) Click on Add a Keyboard and look for Colemak-DH Matrix-Fixed Capital-Custom
10) It should now be added to your system.(Drag it above US(QWERTY) to make it your default). 
11) Give it a quick restart.
12) Now whenever you hit Ctrl+Shift or Win+Space you will be able to cycle between my modded layout and qwerty or whichever other layouts you have.
13) DONE!!!    

In case you want to try doing your own mods in Windows to the layout you can refer to this [forum post](https://forum.colemak.com/topic/870-hacked-msklc-to-enable-remapping-capslock/)

## Manjaro
If you want to use this layout in Manjaro ( should work similarly in any other Arch related distro as well) as well :

1) Go to /usr/share/X11/xkb/symbols/
2) Open a "us" file in the location.
3) Copy the contents from [my "us" file](https://github.com/KenzKD/ColemakDH-Alternative-ANSI/blob/main/us) to the "us" file in your system.
4) Save your file.(It requires admininstrator permission so it should ask you for a password.)
5) Restart your system.
6) Go to your System Settings -> Input Devices -> Keyboard -> Layout -> Add
7) Choose these options. 

![image](https://user-images.githubusercontent.com/65004578/145540602-7d56f286-d32f-4795-a2c1-95aa166521fa.png)

8) Press OK.
9) DONE!!! You should now be able use my modded layout.

In case you want to try doing your own mods in Manjaro to the layout you can refer to this [forum post](https://forum.manjaro.org/t/missing-keyboard-layouts-in-linux-gnome-settings/84404)


## Pictures

What it looks like on my laptop:
![Keyboard ](https://user-images.githubusercontent.com/65004578/120288268-1323d180-c2d1-11eb-9d21-c72f5b15981d.jpg)


What it looks like in the MSKLC software:
![image](https://user-images.githubusercontent.com/65004578/120104077-d2f31080-c163-11eb-9c18-5245aa1a1817.png)

What it looks like in Manjaro:
![image](https://user-images.githubusercontent.com/65004578/145544675-df69d2d0-896d-449b-9ada-482f1638ee51.png)
