import os
import subprocess
from PIL import Image

def convert():
    svg_path = os.path.abspath("server_console_gui/cloud-server-svgrepo-com.svg")
    html_path = os.path.abspath("assets/render_icon.html")
    png_path = os.path.abspath("assets/cloud-server.png")
    ico_path = os.path.abspath("assets/cloud-server.ico")

    with open(svg_path, "r", encoding="utf-8") as f:
        svg_content = f.read()

    html_content = f"""<!DOCTYPE html>
<html>
<head>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: transparent; width: 512px; height: 512px; display: flex; justify-content: center; align-items: center; overflow: hidden; }}
svg {{ width: 480px; height: 480px; }}
</style>
</head>
<body>
{svg_content}
</body>
</html>"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    edge_exe = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    file_url = "file:///" + html_path.replace("\\", "/")
    cmd = [
        edge_exe,
        "--headless",
        "--disable-gpu",
        "--default-background-color=00000000",
        f"--screenshot={png_path}",
        "--window-size=512,512",
        file_url
    ]
    subprocess.run(cmd, check=True)

    if os.path.exists(png_path):
        print("PNG generated successfully:", png_path)
        img = Image.open(png_path)
        img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        print("ICO generated successfully:", ico_path)
    else:
        print("PNG generation failed")

if __name__ == "__main__":
    convert()
