# Stellar Blade FBX Exporter
A modified version of Blender's FBX Exporter to fix flipped bones from Stellar Blade

## Installation
Drag and drop the .zip archive into the blender window and click OK, or navigate to `Edit > Preferences > Get Extensions`

Click the `V` button on the top right and select `Install from Disk...` then select the .zip archive.

<img width="250" height="185" alt="Install from disk... Screenshot" src="https://github.com/user-attachments/assets/83816179-a12f-4e22-8ed3-346a324a3ea0" />

## Export
When you're ready to export, navigate to `File > Export > Stellar Blade FBX (.fbx)`.

<img width="611" height="815" alt="Screenshot 1" src="https://github.com/user-attachments/assets/9c41624a-5f6b-4fa3-8064-13319b15a1c3" />

### Important
The FBX Exporter won't work if you import with Sockets enabled. In case you're importing meshes with `.PSK` format, its required for you to change this option inside FModel.

<img width="866" height="586" alt="463414783-7062aee0-5ef3-4213-9cc0-5958c50c2597" src="https://github.com/user-attachments/assets/ec204fc5-cc08-409c-88c3-0b8689b1ec9a" />


In case you're using `.uemodel` for Mesh formats, there's nothing to do in FModel, but you'll need to make sure you have the `Import Sockets` turned OFF, when importing your mesh to blender, you can disable it in the UEFormat Importer tab.

<img width="230" height="326" alt="463414929-ae89f655-44c4-4ce8-bca9-38bc4a6d3458" src="https://github.com/user-attachments/assets/77d52e82-67a7-434e-97c4-8c6d3ab4a21e" />

## More Information
Be sure to read this [Stellar Blade Modding Wiki Tutorial](https://github.com/Stellar-Blade-Modding-Team/Stellar-Blade-Modding-Guide/wiki/Models) by HeartBee.

## Building Windows releases

Build requirements: 64-bit Windows Python with Tcl/Tk (the standard python.org installer includes it), plus `python -m pip install -r requirements-build.txt`.

- Run `[Build Log Window].bat` to build only the standalone log viewer.
- Run `[Package].bat` to rebuild the viewer and create `releases/stellar-blade-fbx-exporter-v<manifest-version>.zip`.
- To select another Python installation, run `& '.\[Package].ps1' -Python 'C:\Path\To\python.exe'` or pass `-Python` to `[Build Log Window].bat`.

The viewer is built in `dist/StellarBladeExportLog/`, with `StellarBladeExportLog.exe` beside a `dependencies/` folder. Python, Tcl/Tk, and imported modules are distributed externally in this folder instead of a self-extracting EXE. Keep the entire folder together.

The release ZIP includes that complete folder as `log_window/`. The small `addon/stellar_blade_log_window.py` module remains as Blender's launcher and log writer; the GUI source lives in `tools/log_window.py` and is not shipped as a loose script. The old PowerShell viewer is excluded from the ZIP. Installed users do not need Python or PowerShell to open the log viewer. The viewer build targets Windows x64.

## Credits
[AzurieWolf](https://github.com/AzurieWolf),
[ByLemi21](https://github.com/ByLemi21),
[Njaecha](https://github.com/Njaecha),
[HeartBee](https://github.com/StellarBladeModding),
Salt (Providing a list with the inverted bones)

This is a fork of [Blender_SB_FBX_Fixes](https://github.com/ByLemi21/Blender_SB_FBX_Fixes) modified to be a standalone addon.

## Stellar Blade FBX import

The Stellar Blade import panel appears above Include, with Skeleton File and Show Log Window in the same order as the export panel. Bone correction is automatic: importing reverses the exporter's bind-pose flips before Blender builds the armature.

New exports record each bone's flip decision for exact reversal, including posed rigs. Older exports use the selected EVE/Lily skeleton and compare the bind pose with the original FBX bone transforms. Select the same skeleton used for export; legacy detection assumes those model transforms have not been independently reflected by another tool. Unknown, unmarked bones are left unchanged.

The import log lists restored bones and whether they were identified from export metadata or legacy transforms. Blender 5 animation import uses the current Action slot API.

Developers can run the round-trip regression with `blender --background --factory-startup --python-exit-code 1 --python tests/test_stellar_blade_roundtrip.py -- --animation`. Add `--lily --mirrored` to cover Lily and negative armature scale. The test uses a factory scene and temporary FBX files.
