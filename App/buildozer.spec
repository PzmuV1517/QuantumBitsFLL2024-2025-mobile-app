[app]

extra_cflags = -Wno-cast-function-type-strict -Wno-cast-function-type -Wno-error 

extra_ldflags = -Wno-cast-function-type-strict -Wno-cast-function-type

# (str) Title of your application
title = AIDRONe companion app

# (str) Package name
package.name = aidrone

# (str) Package domain (needed for android/ios packaging)
package.domain = org.quantumbits

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas

# (list) List of inclusions using pattern matching
source.include_patterns = assets/*,images/*.png

# (list) Source files to exclude (let empty to not exclude anything)
#source.exclude_exts = spec

# (list) List of directory to exclude (let empty to not exclude anything)
source.exclude_dirs = tests, bin, venv, .venv, __pycache__

# (list) List of exclusions using pattern matching
# Do not prefix with './'
source.exclude_patterns = license,images/*/*.jpg,*.pyc,*.pyo,*.pyd,*.so,*.spec

# (str) Application versioning (method 1)
version = 1.0.0

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy==2.1.0,kivymd==1.1.1,websocket-client,pillow,plyer,cython==0.29.36

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/assets/presplash.png

# (str) Icon of the application
#icon.filename = %(source.dir)s/assets/icon.png

# (list) Supported orientations
# Valid options are: landscape, portrait, portrait-reverse or landscape-reverse
orientation = portrait

# Android specific
#

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
android.permissions = INTERNET, VIBRATE, FOREGROUND_SERVICE, WAKE_LOCK, POST_NOTIFICATIONS

# Add service configuration
# Syntax: ServiceName:EntryPoint[:foreground|:background]
android.services = AIDRONeService:main.py:background

# (int) Target Android API, should be as high as possible.
android.api = 34

# (int) Minimum API your APK / AAB will support.
android.minapi = 23

# (str) Android NDK version to use
android.ndk = 25b

# (bool) If True, then skip trying to update the Android sdk
# This can be useful to avoid excess Internet downloads or save time
# when an update is due and you just want to test/build your package
android.skip_update = False

# (bool) If True, then automatically accept SDK license
# agreements. This is intended for automation only. If set to False,
# the default, you will be shown the license when first running
# buildozer.
android.accept_sdk_license = True

# (bool) Indicate whether the screen should stay on
# Don't forget to add the WAKE_LOCK permission if you set this to True
android.wakelock = True

# (list) The Android archs to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

# (bool) Skip byte compile for .py files
android.no-byte-compile-python = False

# (str) The format used to package the app for release mode (aab or apk or aar).
android.release_artifact = apk

# Change bootstrap approach
p4a.bootstrap = sdl2

# Add build options
p4a.branch = master

# Add debug options to help troubleshoot build issues
android.logcat_filters = *:S python:D

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1

# (str) Path to build artifact storage, absolute or relative to spec file
build_dir = ./.buildozer

# (str) Path to build output (i.e. .apk, .aab, .ipa) storage
bin_dir = ./bin
