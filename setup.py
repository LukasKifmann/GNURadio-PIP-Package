import hashlib
import os
import shutil
import subprocess
import sys
import sysconfig

from setuptools import Extension, find_packages, setup
from setuptools.command.build_ext import build_ext

# Use strictly relative paths for setuptools mapping
WHEEL_PREFIX = os.path.join("build", "wheel", "platlib")
SUPPORTED_PACKAGES = ["gnuradio", "pmt"]

# Bootstrap the directory structure so setuptools validation passes instantly
for pkg in SUPPORTED_PACKAGES:
    pkg_dir = os.path.join(WHEEL_PREFIX, pkg)
    if not os.path.exists(pkg_dir):
        os.makedirs(pkg_dir, exist_ok=True)
        with open(os.path.join(pkg_dir, "__init__.py"), "w") as f:
            f.write("# Staging wrapper\n")


class PIPCMakeExecutor(build_ext):
    def run(self):
        # ----------------------------------------------------------------------
        # FIX 1: BYPASS WINDOWS MAX_PATH (260 chars) LIMIT & CACHE COLLISIONS
        # ----------------------------------------------------------------------
        if sys.platform == "win32":
            # Hash the current source directory to prevent CMakeCache collisions
            # between local dev builds and git-based isolated builds.
            src_path = os.path.abspath(".")
            path_hash = hashlib.md5(src_path.encode("utf-8")).hexdigest()[:6]

            # Force a short, shallow build path (e.g., C:\Users\<Name>\.gr_build_a1b2c3)
            build_temp = os.path.abspath(
                os.path.join(os.path.expanduser("~"), f".gr_build_{path_hash}")
            )
        else:
            build_temp = os.path.abspath(os.path.join("build", "native_compile"))

        os.makedirs(build_temp, exist_ok=True)

        # ----------------------------------------------------------------------
        # FIX 2: ENSURE GIT SUBMODULES ARE CLONED
        # ----------------------------------------------------------------------
        # Pip and Poetry do NOT reliably clone git submodules automatically.
        # GNU Radio relies heavily on them. We must fetch them manually.
        if os.path.exists(".git"):
            print("--- [PIP Automation] Synchronizing Git Submodules ---")
            try:
                subprocess.check_call(
                    ["git", "submodule", "update", "--init", "--recursive"]
                )
            except subprocess.CalledProcessError as e:
                print(
                    f"Warning: Git submodules failed to update. The build may fail. ({e})"
                )

        # Absolute pathing required specifically for CMake contexts
        abs_wheel_prefix = os.path.abspath(WHEEL_PREFIX)
        env = os.environ.copy()

        # Prevent Poetry/PEP-517 from injecting conflicting C compilers into the environment
        if sys.platform == "win32":
            env.pop("CC", None)
            env.pop("CXX", None)

        # ----------------------------------------------------------------------
        # RESOLVE PYTHON PATHS (Uses active environment to match NumPy 2.x)
        # ----------------------------------------------------------------------
        python_executable = os.path.abspath(sys.executable).replace("\\", "/")
        python_include_dir = sysconfig.get_path("include").replace("\\", "/")
        python_library = ""

        if sys.platform == "win32":
            # Base headers on Windows (where Python.h actually lives)
            python_include_dir = os.path.join(sys.base_prefix, "include").replace(
                "\\", "/"
            )

            # Resolve the python link library (e.g. C:/Python312/libs/python312.lib)
            py_ver = f"{sys.version_info.major}{sys.version_info.minor}"
            python_library = os.path.join(
                sys.base_prefix, "libs", f"python{py_ver}.lib"
            ).replace("\\", "/")

        # Define explicit orchestration arguments
        cmake_args = [
            f"-DCMAKE_BINARY_DIR={build_temp}",
            f"-DCMAKE_INSTALL_PREFIX={abs_wheel_prefix}",
            f"-DWHEEL_PREFIX={abs_wheel_prefix}",
            # Modern CMake (3.12+) FindPython3 target specifications
            f"-DPython3_EXECUTABLE={python_executable}",
            f"-DPython3_INCLUDE_DIR={python_include_dir}",
            "-DPython3_FIND_VIRTUALENV=STANDARD",
            # Legacy Python targets (for older nested submodules in GNU Radio)
            f"-DPYTHON_EXECUTABLE={python_executable}",
            f"-DPYTHON_INCLUDE_DIR={python_include_dir}",
        ]

        if sys.platform == "win32":
            if python_library:
                cmake_args.append(f"-DPython3_LIBRARY={python_library}")
                cmake_args.append(f"-DPYTHON_LIBRARY={python_library}")

            # Apply Windows MSVC build specifications
            cmake_args.extend(
                [
                    "-G",
                    "Visual Studio 17 2022",
                    "-A",
                    "x64",
                ]
            )

        # Phase 1: Generation & Configuration
        print("--- [PIP Automation] Configuring Project via CMake ---")
        subprocess.check_call(
            ["cmake", os.path.abspath(".")] + cmake_args, cwd=build_temp, env=env
        )

        # Phase 2: Build & Target Installation
        print("--- [PIP Automation] Compiling and Installing C++ Assets ---")
        build_command = [
            "cmake",
            "--build",
            ".",
            "--config",
            "Release",
            "--target",
            "gnuradio",
        ]

        if sys.platform != "win32":
            build_command.extend(["--", "-j", str(os.cpu_count() or 2)])

        subprocess.check_call(
            build_command,
            cwd=build_temp,
            env=env,
        )

        # ----------------------------------------------------------------------
        # PHASE 3: STAGE COMPILED ASSETS & BUNDLE LIBRARIES FOR PORTABILITY
        # ----------------------------------------------------------------------
        print("--- [PIP Automation] Syncing Compiled Assets to Setuptools Target ---")

        search_root = os.path.abspath(WHEEL_PREFIX)

        # 1. Dynamically locate the ROOT compiled python packages in the build tree
        discovered_packages = {}
        for root, dirs, files in os.walk(search_root):
            for target_pkg in SUPPORTED_PACKAGES:
                if target_pkg in dirs:
                    candidate = os.path.abspath(os.path.join(root, target_pkg))
                    init_file = os.path.join(candidate, "__init__.py")
                    # Ensure it exists and we haven't already mapped it
                    if (
                        os.path.exists(init_file)
                        and target_pkg not in discovered_packages
                    ):
                        with open(init_file, "r") as f:
                            # Ensure it's not our placeholder staging wrapper
                            if "# Staging wrapper" not in f.read():
                                discovered_packages[target_pkg] = candidate

        if not discovered_packages:
            raise RuntimeError("Could not find compiled Python packages!")

        print(f"Discovered root packages: {list(discovered_packages.keys())}")

        print(f"Discovered compiled packages: {list(discovered_packages.keys())}")

        # 2. Synchronize all discovered packages (both gnuradio and pmt)
        for pkg_name, real_dir in discovered_packages.items():
            bootstrap_abs = os.path.abspath(os.path.join(WHEEL_PREFIX, pkg_name))
            packaging_dst = os.path.abspath(os.path.join(self.build_lib, pkg_name))

            if os.path.exists(packaging_dst):
                print(f"Removing placeholder staging directory: {packaging_dst}")
                shutil.rmtree(packaging_dst)

            if os.path.exists(bootstrap_abs):
                print(f"Removing placeholder source directory: {bootstrap_abs}")
                shutil.rmtree(bootstrap_abs)

            print(
                f"Copying '{pkg_name}' package contents to source tree: {bootstrap_abs}"
            )
            shutil.copytree(real_dir, bootstrap_abs)

            print(
                f"Copying '{pkg_name}' package contents to staging area: {packaging_dst}"
            )
            shutil.copytree(real_dir, packaging_dst)

            # 3. Inject Windows DLL Loader hook.
            # On Windows, both gnuradio and pmt must search the main gnuradio package
            # directory to find the companion C++ DLLs.
            print(
                f"Injecting Windows DLL directory loader hook into {pkg_name}/__init__.py..."
            )
            dll_hook = (
                "\n# --- OS PORTABILITY HOOK ---\n"
                "# Windows (Python 3.8+) ignores system PATH for DLLs. We explicitly\n"
                "# register the package directory and its sister gnuradio directory\n"
                "# so bundled companion C++ DLLs are found automatically.\n"
                "import os, sys\n"
                "if sys.platform == 'win32':\n"
                "    _pkg_dir = os.path.dirname(__file__)\n"
                "    _parent_dir = os.path.dirname(_pkg_dir)\n"
                "    _gr_dir = os.path.join(_parent_dir, 'gnuradio')\n"
                "    for d in [_pkg_dir, _gr_dir]:\n"
                "        if os.path.isdir(d):\n"
                "            try:\n"
                "                os.add_dll_directory(d)\n"
                "            except Exception:\n"
                "                pass\n"
                "# ---------------------------\n"
            )
            for init_file_path in [
                os.path.join(bootstrap_abs, "__init__.py"),
                os.path.join(packaging_dst, "__init__.py"),
            ]:
                if os.path.exists(init_file_path):
                    with open(init_file_path, "a") as f:
                        f.write(dll_hook)

        # 4. Search and bundle companion compiled libraries (DLLs/so/dylibs)
        # We consolidate all harvested DLLs inside the 'gnuradio' package to prevent
        # file duplication and keep the wheel size small.
        print("Searching for companion dynamic libraries to bundle into the package...")
        search_paths = [os.path.abspath(WHEEL_PREFIX), os.path.abspath(build_temp)]

        # Resolve target packaging paths for DLL staging
        dll_destinations = []
        pkg = "gnuradio"
        pkg_path = os.path.abspath(os.path.join(self.build_lib, pkg))
        if os.path.exists(pkg_path):
            dll_destinations.append(pkg_path)
        bootstrap_path = os.path.abspath(os.path.join(WHEEL_PREFIX, pkg))
        if os.path.exists(bootstrap_path):
            dll_destinations.append(bootstrap_path)

        if not dll_destinations:
            # Fallback to every package if gnuradio is somehow missing
            for pkg in discovered_packages.keys():
                pkg_path = os.path.abspath(os.path.join(self.build_lib, pkg))
                if os.path.exists(pkg_path):
                    dll_destinations.append(pkg_path)

        bundled_libraries = set()
        for s_path in search_paths:
            if not os.path.exists(s_path):
                continue
            for root, dirs, files in os.walk(s_path):
                # Skip searching inside our newly synced target package directories
                path_parts = os.path.normpath(root).split(os.sep)
                if any(p in path_parts for p in SUPPORTED_PACKAGES):
                    continue
                for file in files:
                    if file.lower().endswith((".dll", ".so", ".dylib")):
                        if file.lower().startswith(
                            ("vcruntime", "msvcp", "api-ms-", "ucrtbase", "concrt")
                        ):
                            continue

                        src_file = os.path.join(root, file)
                        if file.lower() not in bundled_libraries:
                            for dest in dll_destinations:
                                shutil.copy2(src_file, os.path.join(dest, file))
                            bundled_libraries.add(file.lower())
                            print(
                                f" -> Bundled binary library: {file} (from {os.path.relpath(src_file, s_path)})"
                            )

        # 5. Clean up intermediate directories in platlib to avoid packaging leftovers
        print("Cleaning up intermediate directories in platlib...")
        for folder in os.listdir(search_root):
            folder_abs = os.path.join(search_root, folder)
            if os.path.isdir(folder_abs) and folder not in SUPPORTED_PACKAGES:
                # --- PROTECT METADATA FOLDERS ---
                if folder.endswith(".egg-info") or folder.endswith(".dist-info"):
                    continue
                # --------------------------------
                print(f"Removing temporary subdirectory: {folder_abs}")
                shutil.rmtree(folder_abs)

        print(
            "Successfully synchronized compiled modules, typings, and companion libraries!"
        )

        # 6. Purge __pycache__ directories to prevent wheel security warnings
        print("--- [PIP Automation] Scrubbing __pycache__ directories ---")

        # We check both the CMake staging prefix and the setuptools build_lib
        for target_dir in [WHEEL_PREFIX, self.build_lib]:
            if not os.path.exists(target_dir):
                continue

            # topdown=False is required when deleting directories during os.walk
            for root, dirs, files in os.walk(target_dir, topdown=False):
                for d in dirs:
                    if d == "__pycache__":
                        pycache_path = os.path.join(root, d)
                        print(f"Removing bytecode cache: {pycache_path}")

                        shutil.rmtree(pycache_path)


setup(
    name="gnuradio",
    version="3.10.12.0",
    # --- LET SETUPTOOLS FIND ALL NESTED SUBPACKAGES AUTOMATICALLY ---
    packages=find_packages(where=WHEEL_PREFIX),
    # ---------------------------------------------------------------
    package_dir={"": WHEEL_PREFIX},
    package_data={
        "": ["*.pyi", "**/*.pyi", "*.dll", "*.so", "*.dylib", "*.pyd"],
    },
    include_package_data=False,
    ext_modules=[Extension("gnuradio._native", sources=[])],
    cmdclass={"build_ext": PIPCMakeExecutor},
    zip_safe=False,
)
