#!/bin/sh

cd "/Users/main/Downloads/Radiant-Core-main/macos-release-arm64/native"
"/opt/homebrew/bin/cmake" --build "/Users/main/Downloads/Radiant-Core-main/macos-release-arm64/native" --target "test/lint/unicode_src_linter"
"/opt/homebrew/bin/cmake" -E create_symlink "/Users/main/Downloads/Radiant-Core-main/macos-release-arm64/native/test/lint/unicode_src_linter" "/Users/main/Downloads/Radiant-Core-main/macos-release-arm64/test/lint/native-unicode_src_linter"

# Ok let's generate a depfile if we can.
if test "xNinja" = "xNinja"; then
    "/Users/main/Downloads/Radiant-Core-main/cmake/utils/gen-ninja-deps.py" \
        --build-dir "/Users/main/Downloads/Radiant-Core-main/macos-release-arm64/native" \
        --base-dir "/Users/main/Downloads/Radiant-Core-main/macos-release-arm64" \
        --ninja "/opt/homebrew/bin/ninja" \
        "test/lint/native-unicode_src_linter" "test/lint/unicode_src_linter" > "/Users/main/Downloads/Radiant-Core-main/macos-release-arm64/test/lint/native-unicode_src_linter.d"
fi
