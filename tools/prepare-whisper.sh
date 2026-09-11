#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source_dir="$PWD/.native/whisper.cpp"
revision=a8d002cfd879315632a579e73f0148d06959de36
if [[ ! -d "$source_dir/.git" ]]; then
 mkdir -p .native
 git clone --no-checkout https://github.com/ggml-org/whisper.cpp.git "$source_dir"
fi
git -C "$source_dir" fetch origin "$revision"
git -C "$source_dir" checkout --detach "$revision"
[[ "$(git -C "$source_dir" rev-parse HEAD)" == "$revision" ]]
cmake -S "$source_dir" -B build/whisper-host -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DGGML_NATIVE=OFF -DGGML_OPENMP=OFF -DWHISPER_BUILD_SERVER=OFF
cmake --build build/whisper-host --target quantize whisper-cli -j2
python3 tools/prepare-whisper-model.py
sdk="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
for abi in arm64-v8a armeabi-v7a x86_64; do
 cmake -S native/whisper -B "build/whisper-$abi" -DWHISPER_SOURCE="$source_dir" -DCMAKE_TOOLCHAIN_FILE="$sdk/ndk/28.2.13676358/build/cmake/android.toolchain.cmake" -DANDROID_ABI="$abi" -DANDROID_PLATFORM=android-26 -DANDROID_STL=c++_static -DCMAKE_BUILD_TYPE=Release -DANDROID_SUPPORT_FLEXIBLE_PAGE_SIZES=ON
 cmake --build "build/whisper-$abi" --target oldi_whisper -j2
 mkdir -p "app/src/main/jniLibs/$abi"
 cp "build/whisper-$abi/liboldi_whisper.so" "app/src/main/jniLibs/$abi/"
done
mkdir -p app/src/main/assets/third-party
cp "$source_dir/LICENSE" app/src/main/assets/third-party/Whisper-MIT.txt
