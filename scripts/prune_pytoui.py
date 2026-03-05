#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Reverse script to remove directories created by fetch_pytoui.py
"""

import os
import shutil


def prune_pytoui():
    """
    Removes pytoui and pytoui_examples directories if they exist
    """
    # Paths to directories
    dest_path = os.path.expanduser("~/Documents/site-packages/pytoui")
    dest_path2 = os.path.expanduser("~/Documents/pytoui_examples")

    deleted_any = False

    # Remove first directory
    if os.path.exists(dest_path):
        try:
            shutil.rmtree(dest_path)
            print(f"✅ Removed: {dest_path}")
            deleted_any = True
        except Exception as e:
            print(f"❌ Error removing {dest_path}: {e}")
    else:
        print(f"i️ Directory does not exist: {dest_path}")

    # Remove second directory
    if os.path.exists(dest_path2):
        try:
            shutil.rmtree(dest_path2)
            print(f"✅ Removed: {dest_path2}")
            deleted_any = True
        except Exception as e:
            print(f"❌ Error removing {dest_path2}: {e}")
    else:
        print(f"i️ Directory does not exist: {dest_path2}")

    if deleted_any:
        print("\n✨ Cleanup completed successfully!")
    else:
        print("\n📭 Nothing was deleted (directories not found)")


print("🧹 Starting pytoui directories cleanup...\n")
prune_pytoui()
