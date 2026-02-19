# SKÅDIS hook generator for Fusion360

This is a python script that can be used to generate SKÅDIS hooks on a face in Fusion360.

## Installing the script
Place the files in a subfolder in your Fusion360 scripts folder.

## Running the script
Run the script by opening Scripts and Add-Ins and pressing the run button

<img width="458" height="150" alt="image" src="https://github.com/user-attachments/assets/51318908-87ed-4e71-a011-447dd8919d90" />

Select the horizontal edge of your face

<img width="508" height="244" alt="image" src="https://github.com/user-attachments/assets/069d7c8b-014d-4a74-8735-10aa91cd96a6" />

Select the vertical edge of your face

<img width="292" height="497" alt="image" src="https://github.com/user-attachments/assets/d5757e01-1001-4122-98d5-87dd3a7a639c" />

The maximum numer of hooks are placed on the face

<img width="553" height="500" alt="image" src="https://github.com/user-attachments/assets/99f072f7-d1a2-4e79-b46b-0a593ab3aa08" />

## Changing settings
You can tweak the settings in your model

<img width="266" height="81" alt="image" src="https://github.com/user-attachments/assets/c85ec564-25ce-4e79-89c6-d1f2560d515f" />

Or you can adjust the default settings in your script

```python
# -----------------------------
# Constants (mm)
# -----------------------------
WIDTH_MM            = 4.8
HEIGHT_MM           = 7.5
BOARD_DEPTH_MM      = 5.0
HOOK_LENGTH_MM      = 6.0
FILLET_RADIUS_MM    = 1.5
PATTERN_DISTANCE_MM = 40.0   # Skådis grid
DIST_FROM_BOTTOM_MM = 30.0
```
