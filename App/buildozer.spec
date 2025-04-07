[app]

# (str) Title of your application
title = AIDRONe Companion App

# (str) Package name
package.name = aidrone.companion

# (str) Package domain (needed for android/ios packaging)
package.domain = org.quantumbits

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas

# (list) List of inclusions using pattern matching
#source.include_patterns = assets/*,images/*.png

# (list) Source files to exclude (let empty to not exclude anything)
#source.exclude_exts = spec

# (list) List of directory to exclude (let empty to not exclude anything)
#source.exclude_dirs = tests, bin, venv

# (list) List of exclusions using pattern matching
# Do not prefix with './'
#source.exclude_patterns = license,images/*/*.jpg

# (str) Application versioning (method 1)
version = 1.0

# (str) Application versioning (method 2)
# version.regex = __version__ = ['"](.*)['"]
# version.filename = %(source.dir)s/main.py

# (list) Application requirements - specific versions for compatibility
requirements = python3,hostpython3,kivy,kivymd,cython,pyjnius,websocket-client,pillow,certifi

# Add system dependencies
requirements.system = autoconf automake libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
#icon.filename = %(source.dir)s/data/icon.png

# (list) Supported orientations
orientation = portrait

# Android specific
fullscreen = 0
android.presplash_color = #3F51B5
android.permissions = INTERNET, VIBRATE, WAKE_LOCK
android.api = 33
android.minapi = 21
android.ndk = 25b
android.wakelock = True
android.logcat_filters = *:S python:D
android.archs = arm64-v8a
android.allow_backup = True
android.release_artifact = apk
android.no-byte-compile-python = False
android.accept_sdk_license = True
android.apptheme = @android:style/Theme.Material
android.enable_androidx = True

# Fix Java/Gradle settings
android.gradle_dependencies = org.jetbrains.kotlin:kotlin-stdlib:1.9.22
android.gradle_version = 8.2
android.build_tools_version = 33.0.2

# Memory settings for Gradle
android.gradle_options = org.gradle.jvmargs=-Xmx4096m -XX:MaxPermSize=1024m -XX:+HeapDumpOnOutOfMemoryError -Dfile.encoding=UTF-8

[buildozer]
log_level = 2
warn_on_root = 1
# Use explicit build directory to avoid permission issues
build_dir = ./.buildozer
bin_dir = ./bin
