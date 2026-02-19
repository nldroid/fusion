# SKÅDIS hook generator for Fusion360

# SKÅDIS Hook Generator for Autodesk Fusion

A Python-based automation script for **Autodesk Fusion** that instantly generates IKEA SKÅDIS-compatible mounting hooks onto any planar surface.

---

## 📖 Description

This script is designed for makers, engineers, and IKEA enthusiasts who want to bridge the gap between custom CAD design and the popular SKÅDIS pegboard ecosystem. Manual recreation of the SKÅDIS hook geometry—which involves specific tapers, friction-fit tolerances, and precise center-to-center distances—is a tedious and error-prone process. This script automates that entire workflow within the Fusion environment.

### Core Functionality
The script allows users to select any planar face on a solid body and instantly populate it with functional SKÅDIS-style hooks. By leveraging the Fusion API, the script calculates the necessary offsets to ensure that the hooks are perfectly aligned with the standard 20mm horizontal and 40mm vertical spacing of the IKEA system. This ensures that any object you design—whether it is a tool holder, a headphone stand, or a custom shelf—will snap into your pegboard with the same "click" and stability as the original accessories.

### Key Technical Features
* **Adaptive Geometry:** The script doesn't just place a static mesh; it generates native Fusion geometry. This means the hooks are integrated into your component's timeline, allowing for further fillets or modifications.
* **Optimized Tolerances:** Recognizing that 3D printers vary, the script generates hooks with optimized clearances to account for filament expansion, ensuring they aren't too loose to wobble or too tight to snap.
* **Orientation Intelligence:** Users can specify the direction of the "lug" (the part that drops into the slot), allowing for both vertical and horizontal mounting configurations.
* **Face-Bound Validation:** The script checks the dimensions of your selected face to ensure there is enough surface area to support the hook base, preventing "floating" geometry that would fail during a print.

### Workflow Integration
Instead of hunting for STL files of hooks and trying to "Boolean join" them to your models, you simply design your custom holder, run the script, and select the back face. The script handles the complex sweeps and extrusions required to create the characteristic "L-shape" hook profile. This is an essential tool for anyone looking to organize their workspace with professional-grade, bespoke 3D-printed organizers that feel like a native part of the IKEA ecosystem.

---

## 🛠 Installation

1. Download all the files and place the files in a subfolder in your Fusion360 scripts folder (or clone this repository).
2. In **Autodesk Fusion**, go to the **Tools** tab.
3. Select **ADD-INS** > **Scripts and Add-ins**.
4. Click the **plus (+)** icon next to "My Scripts" and select the folder containing the script.
5. Select the script from the list and click **Run**.

6. Select the horizontal edge of your face

<img width="508" height="244" alt="image" src="https://github.com/user-attachments/assets/069d7c8b-014d-4a74-8735-10aa91cd96a6" />

7. Select the vertical edge of your face

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

## 🔒 Privacy Policy

**SKÅDIS Hook Generator** operates with a "Privacy by Design" local-only model:

* **No Data Collection:** This script does not collect, log, or store any personal information.
* **No Data Transmission:** No data is ever sent to a server, third party, or external API. 
* **Local Processing:** All operations are performed strictly on your local machine.

**In short: Your data never leaves your computer.**
