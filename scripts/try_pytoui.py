# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests>=2.32.5",
# ]
# ///
import io
import os
import shutil
import zipfile

import requests


def fetch_and_move_pytoui(user, repo, branch="main"):
    url = f"https://github.com/{user}/{repo}/archive/refs/heads/{branch}.zip"
    dest_path = os.path.expanduser("~/Documents/pytoui-demo/pytoui")
    dest_path2 = os.path.expanduser("~/Documents/pytoui-demo")
    temp_extract_dir = f"{repo}-{branch}"

    print(f"Fetching {url}...")
    response = requests.get(url)

    if response.status_code == 200:
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
            zip_ref.extractall()

        # Paths inside the extracted folder
        src_dir = os.path.join(temp_extract_dir, "src", "pytoui")
        examples_dir = os.path.join(temp_extract_dir, "examples")

        try:
            # Move src/pytoui to ~/Documents/pytoui-demo/pytoui
            if os.path.exists(dest_path):
                shutil.rmtree(dest_path)
            shutil.copytree(src_dir, dest_path)

            # Copy all files from examples to ~/Documents/pytoui-demo
            if os.path.exists(examples_dir):
                for item in os.listdir(examples_dir):
                    s = os.path.join(examples_dir, item)
                    d = os.path.join(dest_path2, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)

            print(
                f"✅ Success! Folder copied to: {dest_path}"
                f" and examples files placed in {dest_path2}",
            )

        finally:
            # Clean up the extracted folder
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)
                print("🧹 Cleaned up temporary files.")
    else:
        print(f"❌ Failed. Status: {response.status_code}")


# Usage
fetch_and_move_pytoui("o-murphy", "pytoui", "main")
