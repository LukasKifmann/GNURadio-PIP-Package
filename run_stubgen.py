import os
import sys
import subprocess

staging_path = sys.argv[1]
lib_dir = os.path.join(staging_path, "lib")

targets = ["pmt", "gnuradio"]

for item in os.listdir(os.path.join(staging_path, "gnuradio")):
    path = os.path.join(staging_path, "gnuradio", item)
    if os.path.isdir(path) and not item.startswith("__"):
        targets.append(f"gnuradio.{item}")

env = os.environ.copy()
env["PYTHONDONTWRITEBYTECODE"] = "1"
env["PYTHONPATH"] = (
    staging_path
    + os.pathsep
    + env.get("PYTHONPATH", "")
)
env["LD_LIBRARY_PATH"] = (
    lib_dir
    + os.pathsep
    + env.get("LD_LIBRARY_PATH", "")
)

for target in targets:
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pybind11_stubgen",
            "--output-dir",
            staging_path,
            target,
        ],
        env=env
    )
