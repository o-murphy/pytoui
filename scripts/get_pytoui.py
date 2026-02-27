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


def fetch_pytoui(user, repo, branch="main"):
    url = f"https://github.com/{user}/{repo}/archive/refs/heads/{branch}.zip"
    dest_path = os.path.expanduser("~/Documents/site-packages/pytoui")
    dest_path2 = os.path.expanduser("~/Documents/pytoui_examples")
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
            # Move src/pytoui to ~/Documents/site-packages/pytoui
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            if os.path.exists(dest_path):
                shutil.rmtree(dest_path)
            shutil.copytree(src_dir, dest_path)

            # Copy all files from examples to ~/Documents/pytoui_examples
            if os.path.exists(examples_dir):
                os.makedirs(dest_path2, exist_ok=True)
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
fetch_pytoui("o-murphy", "pytoui", "main")
