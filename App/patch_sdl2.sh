#!/bin/bash
# Script to patch SDL2 Android sensor code that uses deprecated functions

# Path to SDL androidsensor.c file
SDL_FILE=.buildozer/android/platform/build-arm64-v8a_armeabi-v7a/build/bootstrap_builds/sdl2/jni/SDL/src/sensor/android/SDL_androidsensor.c

# Check if file exists
if [ -f "$SDL_FILE" ]; then
    echo "Patching $SDL_FILE..."
    # Replace ALooper_pollAll with ALooper_pollOnce
    sed -i 's/ALooper_pollAll(0, NULL, \&events, (void \*\*)&source)/ALooper_pollOnce(0, NULL, \&events, (void \*\*)&source)/g' "$SDL_FILE"
    echo "Patch applied"
else
    echo "SDL file not found. Run 'buildozer android clean' first."
fi