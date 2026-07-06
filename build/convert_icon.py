"""
convert_icon.py
---------------
Converts app_icon.jpg to app_icon.ico with multiple sizes (16, 32, 48, 64, 128, 256).
"""

import os
from PIL import Image

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    jpg_path = os.path.join(base_dir, 'assets', 'app_icon.jpg')
    ico_path = os.path.join(base_dir, 'assets', 'app_icon.ico')

    if not os.path.isfile(jpg_path):
        print(f"Error: {jpg_path} not found.")
        return

    print(f"Converting {jpg_path} to {ico_path}...")
    img = Image.open(jpg_path)

    # Ico files should contain multiple sizes for different display resolutions in Windows
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, format='ICO', sizes=sizes)
    print("Icon conversion successful!")

if __name__ == '__main__':
    main()
