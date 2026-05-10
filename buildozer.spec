[app]
title = Atik Avcisi
package.name = atik_avcisi
package.domain = org.atik

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,tflite,txt

version = 1.0

requirements = python3,kivy==2.3.0,numpy,tflite

orientation = portrait
fullscreen = 0

android.permissions = CAMERA,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,INTERNET
android.api = 33
android.fullscreen = 0
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.sdk = 33
android.build_tools_version = 33.0.2
android.archs = arm64-v8a

android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
