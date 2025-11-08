# Packaging & Distribution Options

**Document Purpose:** Technical reference for packaging the Seasonal Baking Tracker for Windows distribution

**Last Updated:** 2025-11-04
**Status:** Reference document - implementation not yet started

---

## Overview

This document outlines options for packaging the Seasonal Baking Tracker Python application into a distributable Windows executable for user testing and eventual production deployment.

**Current State:** Application runs from source with Python 3.12 virtual environment
**Target State:** Single-click installable application for Windows users without Python

---

## Packaging Tool Comparison

### 1. PyInstaller (Recommended for Initial Release)

**Best for:** Quick deployment, user testing, most common use case

**Pros:**
- Most widely used and well-documented
- Works well with CustomTkinter
- Creates single executable or folder distribution
- No Python installation required on target machine
- Active community support
- Extensive troubleshooting resources

**Cons:**
- Executable size can be large (50-100+ MB)
- Antivirus may flag executables (false positive)
- Initial build setup requires testing
- Slower startup than compiled solutions

**Typical Output Size:** 60-100 MB

**Installation:**
```bash
pip install pyinstaller
```

**Basic Usage:**
```bash
# Create spec file (one-time setup)
pyi-makespec --onedir --windowed --name="BakeTracker" src/main.py

# Build executable
pyinstaller BakeTracker.spec

# Output: dist/BakeTracker/BakeTracker.exe
```

**CustomTkinter-specific Configuration:**

Edit `BakeTracker.spec`:

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include CustomTkinter assets
        ('venv/Lib/site-packages/customtkinter', 'customtkinter'),
    ],
    hiddenimports=['customtkinter'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BakeTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress with UPX
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico'  # Optional: Add application icon
)
```

**One-file vs One-folder:**
- `--onefile`: Single .exe (slower startup, cleaner)
- `--onedir`: Folder with exe + dependencies (faster startup, many files)

**Recommendation:** Use `--onedir` for testing, consider `--onefile` for final release

---

### 2. Nuitka (Better Performance)

**Best for:** Production release, performance-critical deployment

**Pros:**
- Compiles Python to C - faster execution
- Smaller executable than PyInstaller
- Better performance (faster startup, lower memory)
- Less likely to trigger antivirus (native code)
- Can achieve near-native performance

**Cons:**
- Longer compilation time (5-10 minutes vs 1-2 for PyInstaller)
- More complex setup
- Requires C compiler (Visual Studio Build Tools)
- Less community resources than PyInstaller
- More difficult to debug packaging issues

**Typical Output Size:** 40-70 MB (smaller than PyInstaller)

**Prerequisites:**
- Visual Studio Build Tools (free download from Microsoft)
- Recommended: VS 2019 or 2022 Build Tools

**Installation:**
```bash
pip install nuitka
```

**Usage:**
```bash
python -m nuitka --standalone --onefile \
    --windows-disable-console \
    --enable-plugin=tk-inter \
    --include-package=customtkinter \
    --include-data-dir=venv/Lib/site-packages/customtkinter=customtkinter \
    --output-dir=dist \
    --windows-icon-from-ico=assets/icon.ico \
    src/main.py
```

**Compilation Time:** 5-10 minutes (first build), 2-5 minutes (subsequent)

**Recommendation:** Consider for production after PyInstaller testing successful

---

### 3. cx_Freeze (Alternative to PyInstaller)

**Best for:** Cross-platform deployment, if targeting Linux/Mac later

**Pros:**
- Cross-platform (Windows, macOS, Linux)
- Good SQLite support out of the box
- Simpler than PyInstaller for some use cases
- Official Python packaging recommendation

**Cons:**
- Less popular than PyInstaller (fewer examples)
- Less documentation for CustomTkinter specifically
- Smaller community
- May require more troubleshooting

**Typical Output Size:** 60-90 MB

**Installation:**
```bash
pip install cx_Freeze
```

**Setup File (`setup.py`):**
```python
from cx_Freeze import setup, Executable

build_exe_options = {
    "packages": ["customtkinter", "tkinter", "sqlalchemy"],
    "include_files": [
        ("venv/Lib/site-packages/customtkinter", "lib/customtkinter"),
    ],
    "excludes": ["test", "unittest"],
}

setup(
    name="BakeTracker",
    version="0.3.0",
    description="Seasonal Baking Tracker",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            "src/main.py",
            base="Win32GUI",
            target_name="BakeTracker.exe",
            icon="assets/icon.ico"
        )
    ]
)
```

**Usage:**
```bash
python setup.py build
# Output: build/exe.win-amd64-3.12/BakeTracker.exe
```

**Recommendation:** Skip unless cross-platform deployment becomes a requirement

---

## Installer Creation (Post-Bundling)

After creating an executable with PyInstaller/Nuitka, create a professional Windows installer.

### Option A: Inno Setup (Recommended)

**Best for:** Professional Windows installation experience

**Pros:**
- Free and open-source
- Industry standard (used by many commercial apps)
- Creates professional .exe installer
- Handles shortcuts, uninstall, registry, file associations
- Very small installer size (wraps your app)
- Excellent documentation

**Cons:**
- Requires learning Inno Setup scripting language
- Windows-only

**Download:** [https://jrsoftware.org/isinfo.php](https://jrsoftware.org/isinfo.php)

**Sample Script (`installer.iss`):**

```ini
[Setup]
AppName=Seasonal Baking Tracker
AppVersion=0.3.0
AppPublisher=Your Name
DefaultDirName={autopf}\BakeTracker
DefaultGroupName=Baking Tracker
OutputDir=installer_output
OutputBaseFilename=BakeTracker_Setup_v0.3.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\BakeTracker.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"

[Files]
Source: "dist\BakeTracker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Baking Tracker"; Filename: "{app}\BakeTracker.exe"
Name: "{group}\Uninstall Baking Tracker"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Baking Tracker"; Filename: "{app}\BakeTracker.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\BakeTracker.exe"; Description: "Launch Baking Tracker"; Flags: postinstall nowait skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\BakeTracker"
Type: filesandordirs; Name: "{userdocs}\BakeTracker"
```

**Compile:**
1. Open Inno Setup Compiler
2. Load `installer.iss`
3. Click "Compile"
4. Output: `installer_output/BakeTracker_Setup_v0.3.0.exe`

---

### Option B: NSIS (Nullsoft Scriptable Install System)

**Best for:** Advanced customization, plugin support

**Pros:**
- Very powerful and flexible
- Plugin system for advanced features
- Used by many professional applications (Firefox, VLC)
- Small installer overhead

**Cons:**
- More complex scripting language than Inno Setup
- Steeper learning curve
- Less modern UI by default

**Download:** [https://nsis.sourceforge.io/](https://nsis.sourceforge.io/)

**Recommendation:** Use Inno Setup unless specific NSIS features are needed

---

## Distribution Strategies

### For User Testing (Quick & Simple)

**Portable Folder Distribution:**

```bash
# Build with PyInstaller --onedir
pyinstaller --onedir --windowed --name="BakeTracker" src/main.py

# ZIP the entire dist/BakeTracker folder
# Include README_INSTALL.txt with instructions
```

**Pros:**
- No installation needed
- Easy to update (replace exe)
- Users can run from any location
- Good for testing phase

**Cons:**
- Many files (looks unprofessional)
- Users might accidentally delete dependencies
- No uninstaller
- No shortcuts created

**Distribution Size:** 70-100 MB (zipped: 30-50 MB)

---

### For Production Release

**Recommended Approach:**

1. **Build with PyInstaller or Nuitka** → Creates executable
2. **Package with Inno Setup** → Creates installer
3. **Optionally code sign** → Reduces antivirus warnings

**Distribution:**
- Host installer on website/Google Drive/Dropbox
- Users download and run single .exe installer
- Installer handles shortcuts, uninstall, file associations

---

## Important Considerations

### Database Location

Current configuration:
```
C:\Users\[Username]\Documents\BakeTracker\bake_tracker.db
```

**Why this is good:**
- User-specific (works for all Windows users)
- Persists across application updates
- Standard location for user data
- Backed up with documents

**What to verify:**
- Application creates directory if it doesn't exist
- Proper error handling if directory is read-only
- Consider allowing custom database location in future

### Code Signing (Optional but Recommended)

**Without Code Signing:**
- Windows SmartScreen warnings
- Antivirus may quarantine
- "Unknown publisher" warnings

**With Code Signing:**
- Trusted by Windows
- Fewer antivirus issues
- Professional appearance

**Cost:** ~$100-400/year for code signing certificate

**Providers:**
- DigiCert
- Sectigo
- GlobalSign

**For testing:** Not required, users can bypass warnings

---

## Known Issues & Solutions

### Issue 1: Antivirus False Positives

**Problem:** Bundled executables often trigger antivirus warnings

**Solutions:**
1. Code sign the executable (best solution)
2. Use Nuitka instead of PyInstaller (less likely to trigger)
3. Submit to antivirus vendors for whitelisting
4. Document workaround for users (add to exclusions)

**For Testing:**
- Add to Windows Defender exclusions
- Inform testers this is normal for unsigned apps

---

### Issue 2: Missing CustomTkinter Assets

**Problem:** Application runs from source but fails when bundled

**Solution:**
```python
# In BakeTracker.spec, ensure:
datas=[
    ('venv/Lib/site-packages/customtkinter', 'customtkinter'),
],
```

**Testing:**
- Test on clean Windows VM
- Test on machine without Python installed
- Verify all UI elements render correctly

---

### Issue 3: Large File Size

**Problem:** Bundled application is 60-100 MB

**Solutions:**
1. **Use UPX compression** (in PyInstaller spec)
   - Reduces size by 30-50%
   - May trigger some antivirus

2. **Exclude unnecessary modules:**
   ```python
   excludes=['test', 'unittest', 'email', 'http', 'xml']
   ```

3. **Use Nuitka** (naturally smaller)

4. **Consider implications:**
   - 60-100 MB is acceptable for modern systems
   - One-time download
   - Includes entire Python runtime + dependencies

---

### Issue 4: Slow Startup (PyInstaller --onefile)

**Problem:** Application takes 5-10 seconds to start with --onefile

**Cause:** Temporary extraction on every launch

**Solutions:**
1. Use `--onedir` instead (instant startup)
2. Use Nuitka (compiled, fast startup)
3. Document expected startup time

---

## Testing Checklist

Before distributing to users:

**Build Testing:**
- [ ] Application builds without errors
- [ ] Executable runs on build machine
- [ ] All UI elements display correctly
- [ ] Database operations work
- [ ] Import/export functions work

**Clean Machine Testing:**
- [ ] Test on Windows machine without Python
- [ ] Test on Windows 10 and Windows 11
- [ ] Verify database directory creation
- [ ] Test with different user accounts
- [ ] Check Windows Defender behavior

**Functionality Testing:**
- [ ] All CRUD operations work
- [ ] Cost calculations accurate
- [ ] Event planning features functional
- [ ] Shopping list generation works
- [ ] Application closes cleanly

**Installation Testing (if using installer):**
- [ ] Installer runs without errors
- [ ] Shortcuts created correctly
- [ ] Application launches from shortcuts
- [ ] Uninstaller removes all files
- [ ] No registry pollution after uninstall

---

## Recommended Workflow

### Phase 1: Initial Testing (Current)

1. Use **PyInstaller --onedir**
2. Distribute as ZIP file
3. Include simple README with instructions
4. Gather feedback from 2-3 testers

**Timeline:** 1-2 hours setup, immediate distribution

---

### Phase 2: Wider Testing

1. Continue with **PyInstaller --onedir**
2. Create **Inno Setup installer**
3. Distribute installer .exe
4. Gather feedback from 5-10 testers

**Timeline:** 2-3 hours setup, 1-2 weeks testing

---

### Phase 3: Production Release

1. Evaluate PyInstaller vs Nuitka performance
2. Create professional **Inno Setup installer**
3. Consider **code signing** (optional)
4. Create versioned releases
5. Host on website or GitHub releases

**Timeline:** 4-8 hours setup + code signing process

---

## File Structure for Packaging

```
bake-tracker/
├── src/                          # Application source
├── docs/                         # Documentation
├── assets/                       # Icons, images
│   └── icon.ico                 # Application icon (256x256)
├── build/                        # Build artifacts (gitignored)
├── dist/                         # Distribution output (gitignored)
├── installer_output/             # Installer output (gitignored)
├── BakeTracker.spec           # PyInstaller configuration
├── installer.iss                # Inno Setup script
├── build.py                     # Automated build script
└── README_INSTALL.txt           # User installation instructions
```

---

## Automation Script (Future)

**Purpose:** Automate the entire build process

**Features:**
- Clean previous builds
- Run PyInstaller
- Run tests on bundled executable
- Create installer with Inno Setup
- Generate checksums
- Create release notes

**Implementation:** Python script using `subprocess` module

**Not included in this document:** Will be created when packaging is implemented

---

## Resources

**PyInstaller:**
- Documentation: https://pyinstaller.org/
- CustomTkinter Guide: https://github.com/TomSchimansky/CustomTkinter/wiki/Packaging

**Nuitka:**
- Documentation: https://nuitka.net/
- User Manual: https://nuitka.net/doc/user-manual.html

**Inno Setup:**
- Website: https://jrsoftware.org/isinfo.php
- Documentation: https://jrsoftware.org/ishelp/

**Code Signing:**
- DigiCert: https://www.digicert.com/code-signing
- Guide: https://docs.microsoft.com/en-us/windows/win32/seccrypto/signtool

---

## Future Considerations

**Auto-Update System:**
- Check for updates on startup
- Download and install updates
- Requires update server/hosting

**Cross-Platform:**
- macOS build using PyInstaller
- Linux build using PyInstaller or AppImage
- Shared codebase already compatible

**Microsoft Store Distribution:**
- MSIX packaging
- Automatic updates
- Wider reach
- Requires Microsoft developer account ($19/year individual)

---

**Document Status:** Reference document for future packaging implementation
**Next Action:** Add packaging task to DEVELOPMENT_STATUS.md as planned feature
