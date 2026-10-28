#!/bin/bash
set -e

SRC="/workspace/course/configs"
DST="/workspace/chipyard/generators/chipyard/src/main/scala/config"

if [ ! -d "$SRC" ]; then
    echo "Course configuration directory not found: $SRC"
    exit 1
fi

echo "Linking course Chipyard configurations..."

for file in "$SRC"/*.scala; do
    if [ -e "$file" ]; then
        name=$(basename "$file")

        ln -sf "$file" "$DST/$name"

        echo "  $name"
    fi
done

echo "Course configurations ready."

# Student hardware belongs on the main source path; test suites do not.
# Retain the directory tree so two projects may use the same filename.
STUDENT_SRC="/workspace/student-work"
STUDENT_DST="/workspace/chipyard/generators/chipyard/src/main/scala/student-work"
mkdir -p "$STUDENT_DST"
if [ -d "$STUDENT_SRC" ]; then
    while IFS= read -r -d '' file; do
        relative="${file#"$STUDENT_SRC/"}"
        case "$relative" in
            src/test/*|test/*|tests/*|*/src/test/*|*/test/*|*/tests/*|*Spec.scala|build/*|target/*|*/build/*|*/target/*) continue ;;
        esac
        mkdir -p "$STUDENT_DST/$(dirname "$relative")"
        ln -sf "$file" "$STUDENT_DST/$relative"
        echo "  student-work/$relative"
    done < <(find "$STUDENT_SRC" -type f -name '*.scala' -print0)
fi
