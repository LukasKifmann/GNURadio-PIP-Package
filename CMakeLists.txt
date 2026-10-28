cmake_minimum_required(VERSION 3.24)
project(gnuradio-pip-package)

include(ExternalProject)
if (NOT WIN32)
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(SNDFILE REQUIRED sndfile)
    
    include_directories(${SNDFILE_INCLUDE_DIRS})
    link_directories(${SNDFILE_LIBRARY_DIRS})
    
    find_package(Python REQUIRED COMPONENTS Interpreter)
    set(PYTHON_EXECUTABLE "${Python_EXECUTABLE}")

    execute_process(
        COMMAND ${PYTHON_EXECUTABLE}
                -c "import sysconfig; print(sysconfig.get_path('platlib'))"
        OUTPUT_VARIABLE SP_DIR
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
                    
    ExternalProject_Add(
        gnuradio
        GIT_REPOSITORY https://github.com/gnuradio/gnuradio.git
        GIT_TAG v3.10.12.0
        SOURCE_DIR ${CMAKE_BINARY_DIR}/gnuradio-src
        BINARY_DIR ${CMAKE_BINARY_DIR}/gnuradio-build
        INSTALL_DIR ${CMAKE_INSTALL_PREFIX}
        CMAKE_ARGS
            -DCMAKE_PREFIX_PATH=<INSTALL_DIR>
            -DCMAKE_INSTALL_PREFIX=<INSTALL_DIR>
            -DCMAKE_INSTALL_RPATH=${SP_DIR}/lib
            -DCMAKE_BUILD_WITH_INSTALL_RPATH=TRUE
            -DCMAKE_INSTALL_RPATH_USE_LINK_PATH=TRUE
            -DPYTHON_EXECUTABLE=${PYTHON_EXECUTABLE}
            -DPYTHON_SITE_PACKAGES=${SP_DIR}
            -DENABLE_PYTHON=ON
            -DENABLE_GR_AUDIO=ON
            -DENABLE_GR_BLOCKS=ON
            -DENABLE_GR_ANALOG=ON
            -DENABLE_GR_FILTER=ON
            -DENABLE_GR_FFT=ON
            -DAUDIO_BACKEND=alsa
            -DHAVE_LIBSNDFILE=TRUE
    )
else()
    # ==============================================================================
    # PYTHON DETECTION & RECOVERY
    # ==============================================================================
    # Prioritize Python path bindings passed down from setup.py
    if(DEFINED PYTHON_EXECUTABLE)
        set(Python_EXECUTABLE "${PYTHON_EXECUTABLE}")
    elseif(DEFINED Python3_EXECUTABLE)
        set(Python_EXECUTABLE "${Python3_EXECUTABLE}")
    elseif(NOT DEFINED Python_EXECUTABLE)
        find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)
    endif()
    
    # Resolve true base Python include directory (where Python.h actually lives)
    if(DEFINED Python3_INCLUDE_DIR)
        set(PYTHON_REAL_INCLUDE_DIR "${Python3_INCLUDE_DIR}")
    elseif(DEFINED PYTHON_INCLUDE_DIR)
        set(PYTHON_REAL_INCLUDE_DIR "${PYTHON_INCLUDE_DIR}")
    else()
        execute_process(
            COMMAND ${Python_EXECUTABLE} -c "import sysconfig; print(sysconfig.get_path('include'), end='')"
            OUTPUT_VARIABLE PYTHON_REAL_INCLUDE_DIR
            OUTPUT_STRIP_TRAILING_WHITESPACE
        )
    endif()
    file(TO_CMAKE_PATH "${PYTHON_REAL_INCLUDE_DIR}" PYTHON_REAL_INCLUDE_DIR)
    
    # Resolve true base Python link library (.lib) for Windows linking
    if(DEFINED Python3_LIBRARY)
        set(PYTHON_REAL_LIBRARY "${Python3_LIBRARY}")
    elseif(DEFINED PYTHON_LIBRARY)
        set(PYTHON_REAL_LIBRARY "${PYTHON_LIBRARY}")
    else()
        if(WIN32)
            execute_process(
                COMMAND ${Python_EXECUTABLE} -c "import sys; print(sys.prefix)"
                OUTPUT_VARIABLE PYTHON_SYS_PREFIX_RAW
                OUTPUT_STRIP_TRAILING_WHITESPACE
            )
            file(TO_CMAKE_PATH "${PYTHON_SYS_PREFIX_RAW}" CLEAN_SYS_PREFIX)
            execute_process(
                COMMAND ${Python_EXECUTABLE} -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}', end='')"
                OUTPUT_VARIABLE PY_VER_SHORT
            )
            set(PYTHON_REAL_LIBRARY "${CLEAN_SYS_PREFIX}/libs/python${PY_VER_SHORT}.lib")
        else()
            set(PYTHON_REAL_LIBRARY "")
        endif()
    endif()
    if(PYTHON_REAL_LIBRARY)
        file(TO_CMAKE_PATH "${PYTHON_REAL_LIBRARY}" PYTHON_REAL_LIBRARY)
    endif()
    
    # Set up staging destination prefixes
    set(SP_DIR "Lib/site-packages")
    set(AUDIO_BACKEND "windows")
    
    if(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT OR NOT CMAKE_INSTALL_PREFIX)
        set(WHEEL_PREFIX "${CMAKE_BINARY_DIR}/wheel_staging")
    else()
        set(WHEEL_PREFIX "${CMAKE_INSTALL_PREFIX}")
    endif()
    
    file(TO_CMAKE_PATH "${WHEEL_PREFIX}" CLEAN_WHEEL_PREFIX)
    file(MAKE_DIRECTORY "${CLEAN_WHEEL_PREFIX}/include")
    file(MAKE_DIRECTORY "${CLEAN_WHEEL_PREFIX}/lib")
    
    # Retrieve remaining environment dependencies relative to interpreter
    execute_process(
        COMMAND ${Python_EXECUTABLE} -c "import pybind11; print(pybind11.get_cmake_dir())"
        OUTPUT_VARIABLE PYBIND11_COMPUTED_DIR
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
    file(TO_CMAKE_PATH "${PYBIND11_COMPUTED_DIR}" CLEAN_PYBIND11_DIR)
    
    execute_process(
        COMMAND ${Python_EXECUTABLE} -c "import numpy; print(numpy.get_include())"
        OUTPUT_VARIABLE NUMPY_INCLUDE_DIR
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
    file(TO_CMAKE_PATH "${NUMPY_INCLUDE_DIR}" CLEAN_NUMPY_INCLUDE_DIR)
    
    execute_process(
        COMMAND ${Python_EXECUTABLE} -c "import site; print(site.getsitepackages()[0])"
        OUTPUT_VARIABLE PYTHON_SITE_PACKAGES
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
    file(TO_CMAKE_PATH "${PYTHON_SITE_PACKAGES}" CLEAN_SITE_PACKAGES)
    
    execute_process(
        COMMAND ${Python_EXECUTABLE} -c "import sys; print(sys.prefix)"
        OUTPUT_VARIABLE PYTHON_SYS_PREFIX
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
    file(TO_CMAKE_PATH "${PYTHON_SYS_PREFIX}" CLEAN_SYS_PREFIX)
    
    message(STATUS "Normalized Slotted Prefixes: ${CLEAN_SYS_PREFIX} ; ${CLEAN_SITE_PACKAGES} ; ${CLEAN_WHEEL_PREFIX}")
    message(STATUS "Using Base Python Include: ${PYTHON_REAL_INCLUDE_DIR}")
    message(STATUS "Using Base Python Library: ${PYTHON_REAL_LIBRARY}")
    
    set(ENV{INCLUDE} "$ENV{INCLUDE};${CLEAN_WHEEL_PREFIX}/include")
    
    # ==============================================================================
    # HACK: Force-generate missing afxres.h header for rc.exe
    # ==============================================================================
    set(HACK_INCLUDE_DIR "${CMAKE_BINARY_DIR}/rc_hacks")
    file(MAKE_DIRECTORY "${HACK_INCLUDE_DIR}")
    file(WRITE "${HACK_INCLUDE_DIR}/afxres.h" "// MFC Fallback\n#include <winres.h>\n")
    
    # ==============================================================================
    # EXTERNAL DEPENDENCIES COMPILATION
    # ==============================================================================
    ExternalProject_Add(
        libsndfile_ext
        GIT_REPOSITORY https://github.com/libsndfile/libsndfile.git
        GIT_TAG 1.2.2
        CMAKE_ARGS
            -DCMAKE_POLICY_VERSION_MINIMUM=3.5
            -DCMAKE_BUILD_TYPE=Release
            -DCMAKE_INSTALL_PREFIX=${CLEAN_WHEEL_PREFIX}
            -DBUILD_PROGRAMS=OFF
            -DBUILD_EXAMPLES=OFF
            -DBUILD_TESTING=OFF
            -DENABLE_EXTERNAL_LIBS=OFF
    )
    
    ExternalProject_Add(
        volk_ext
        GIT_REPOSITORY https://github.com/gnuradio/volk.git
        GIT_TAG v3.1.0
        CMAKE_ARGS
            -DCMAKE_BUILD_TYPE=Release
            -DCMAKE_INSTALL_PREFIX=${CLEAN_WHEEL_PREFIX}
            -DENABLE_TESTING=OFF
            -DENABLE_PROFILING=OFF
            "-DPYTHON_EXECUTABLE=${Python_EXECUTABLE}"
            "-DPython3_EXECUTABLE=${Python_EXECUTABLE}"
    )
    
    ExternalProject_Add(
        spdlog_ext
        GIT_REPOSITORY https://github.com/gabime/spdlog.git
        GIT_TAG v1.12.0
        CMAKE_ARGS
            -DCMAKE_BUILD_TYPE=Release
            -DCMAKE_INSTALL_PREFIX=${CLEAN_WHEEL_PREFIX}
            -DSPDLOG_BUILD_EXAMPLES=OFF
            -DSPDLOG_BUILD_TESTS=OFF
    )
    
    ExternalProject_Add(
        fftw3f_ext
        URL "https://www.fftw.org/fftw-3.3.11.tar.gz"
        CMAKE_ARGS
            -DCMAKE_BUILD_TYPE=Release
            -DCMAKE_INSTALL_PREFIX=${CLEAN_WHEEL_PREFIX}
            -DCMAKE_POLICY_VERSION_MINIMUM=3.5
            -DENABLE_FLOAT=ON
            -DENABLE_SSE2=ON
            -DENABLE_AVX=ON
            -DBUILD_TESTS=OFF
    )
    
    ExternalProject_Add(
        boost_ext
        URL "https://archives.boost.io/release/1.82.0/binaries/boost_1_82_0-bin-msvc-all-32-64.7z"
        CONFIGURE_COMMAND ""
        BUILD_COMMAND ""
        INSTALL_COMMAND ${CMAKE_COMMAND} -E copy_directory <SOURCE_DIR>/boost ${CLEAN_WHEEL_PREFIX}/include/boost
        COMMAND ${CMAKE_COMMAND} -E copy_directory <SOURCE_DIR>/lib64-msvc-14.3 ${CLEAN_WHEEL_PREFIX}/lib
        COMMAND ${CMAKE_COMMAND} -E copy_directory <SOURCE_DIR>/lib64-msvc-14.3/cmake ${CLEAN_WHEEL_PREFIX}/lib/cmake
    )
    
    ExternalProject_Add(gmp_ext
        URL "https://github.com/ShiftMediaProject/gmp/releases/download/6.2.1/libgmp_6.2.1_msvc14.zip"
        PREFIX "${CMAKE_BINARY_DIR}/gmp"
        CONFIGURE_COMMAND ""
        BUILD_COMMAND ""
        INSTALL_COMMAND ${CMAKE_COMMAND} -E copy_directory <SOURCE_DIR>/include ${CLEAN_WHEEL_PREFIX}/include
                COMMAND ${CMAKE_COMMAND} -E copy_directory <SOURCE_DIR>/lib/x64 ${CLEAN_WHEEL_PREFIX}/lib
                # --- THIS IS THE MISSING LINE ---
                COMMAND ${CMAKE_COMMAND} -E copy_directory <SOURCE_DIR>/bin/x64 ${CLEAN_WHEEL_PREFIX}/bin
    )
    set(GMP_INC_DIR "${CLEAN_WHEEL_PREFIX}/include")
    set(GMP_LIB_PATH "${CLEAN_WHEEL_PREFIX}/lib/gmp.lib")
    set(GMPXX_LIB_PATH "${CLEAN_WHEEL_PREFIX}/lib/gmp.lib")
    
    # ==============================================================================
    # COMPILER FLAGS CONFIGURATION
    # ==============================================================================
    # Explicitly append our true Python include dir directly into compiler flags as a permanent fallback
    set(GR_CXX_FLAGS "/EHsc /GR /DBOOST_ALL_NO_LIB /I\"${CLEAN_WHEEL_PREFIX}/include\" /I\"${PYTHON_REAL_INCLUDE_DIR}\"")
    set(GR_C_FLAGS "/I\"${CLEAN_WHEEL_PREFIX}/include\" /I\"${PYTHON_REAL_INCLUDE_DIR}\"")
    
    # ==============================================================================
    # STUB GENERATION HELPER SCRIPT
    # ==============================================================================
    set(STUBGEN_SCRIPT "${CMAKE_BINARY_DIR}/run_stubgen.py")
    file(WRITE "${STUBGEN_SCRIPT}" "
    import os, sys, subprocess
    
    # Raw paths from CMake
    staging_path = r'${CLEAN_WHEEL_PREFIX}/${SP_DIR}'
    bin_dir = r'${CLEAN_WHEEL_PREFIX}/bin'
    lib_dir = r'${CLEAN_WHEEL_PREFIX}/lib'
    gnuradio_dir = r'${CLEAN_WHEEL_PREFIX}/${SP_DIR}/gnuradio'
    
    # CRITICAL FIX: Convert CMake forward slashes (/) to Windows backslashes (\)
    staging_path = os.path.abspath(os.path.normpath(staging_path))
    bin_dir = os.path.abspath(os.path.normpath(bin_dir))
    lib_dir = os.path.abspath(os.path.normpath(lib_dir))
    gnuradio_dir = os.path.abspath(os.path.normpath(gnuradio_dir))
    
    print('--- [Stubgen Lifecycle] Staging path: ' + staging_path + ' ---')
    
    targets = []
    if os.path.exists(os.path.join(staging_path, 'pmt')):
        targets.append('pmt')
    
    if os.path.exists(gnuradio_dir):
        targets.append('gnuradio')
        for item in os.listdir(gnuradio_dir):
            item_path = os.path.join(gnuradio_dir, item)
            if os.path.isdir(item_path) and not item.startswith('__'):
                targets.append('gnuradio.' + item)
    
    for target in targets:
        print('Executing stub generation for: ' + target)
        
        # Safely construct the runner script without f-string escaping collisions
        lines = [
            'import os, sys',
            'sys.path.insert(0, ' + repr(staging_path) + ')',
            'if sys.platform == \"win32\":',
            '    for d in [' + repr(bin_dir) + ', ' + repr(lib_dir) + ', ' + repr(gnuradio_dir) + ']:',
            '        if os.path.isdir(d):',
            '            try:',
            '                os.add_dll_directory(d)',
            '            except Exception as e:',
            '                print(\"WARNING: os.add_dll_directory failed for \" + d + \" -> \" + str(e))',
            '    # Fallback for older legacy DLL loaders',
            '    os.environ[\"PATH\"] = ' + repr(bin_dir) + ' + os.pathsep + ' + repr(lib_dir) + ' + os.pathsep + os.environ.get(\"PATH\", \"\")',
            'from pybind11_stubgen import main',
            'sys.argv = [\"pybind11_stubgen\", \"--output-dir\", ' + repr(staging_path) + ', ' + repr(target) + ']',
            'main()'
        ]
        
        runner_code = chr(10).join(lines)
        
        res = subprocess.run([sys.executable, '-c', runner_code], capture_output=True, text=True)
        if res.returncode != 0:
            print('STUBGEN ERROR for ' + target + ':')
            print(res.stderr)
        else:
            print('Successfully generated .pyi for ' + target)
    ")
    
    # ==============================================================================
    # MAIN GNU RADIO COMPILATION PHASE
    # ==============================================================================
    set(GR_CMAKE_ARGS
        "-DCMAKE_INSTALL_PREFIX=${CLEAN_WHEEL_PREFIX}"
        "-DCMAKE_PREFIX_PATH=${CLEAN_SYS_PREFIX};${CLEAN_SITE_PACKAGES};${CLEAN_WHEEL_PREFIX}"
        "-DCMAKE_BUILD_TYPE=Release"
        -DMPLIB=gmp_fallback
        "-DCMAKE_CXX_FLAGS=${GR_CXX_FLAGS}"
        "-DCMAKE_C_FLAGS=${GR_C_FLAGS}"
        "-DCMAKE_REQUIRED_INCLUDES=${CLEAN_WHEEL_PREFIX}/include;${PYTHON_REAL_INCLUDE_DIR}"
        "-DCMAKE_RC_FLAGS=/I\"${HACK_INCLUDE_DIR}\""    
        
        # SYSTEM COMPONENT SWITCHES
        -DENABLE_GR_FFT=ON
        -DENABLE_GR_FILTER=ON
        -DENABLE_GR_ANALOG=ON
        -DENABLE_GR_BLOCKS=ON
        
        # --- VOLK HARD-INJECTION ---
        -DENABLE_VOLK=ON
        "-DVOLK_INCLUDE_DIRS=${CLEAN_WHEEL_PREFIX}/include"
        "-DVOLK_LIBRARIES=${CLEAN_WHEEL_PREFIX}/lib/volk.lib"
        "-DVOLK_IMPLEMENTATION_LIST=generic"
        "-DVOLK_FOUND=TRUE"
        "-DVolk_FOUND=TRUE"
        
        # PYTHON DEPENDENCY RECOVERY (No reference to virtualenv includes/libs anymore!)
        "-DPython3_INCLUDE_DIR=${PYTHON_REAL_INCLUDE_DIR}"
        "-DPython3_LIBRARY=${PYTHON_REAL_LIBRARY}"
        "-Dpybind11_DIR=${CLEAN_PYBIND11_DIR}"
        -DCMAKE_POLICY_DEFAULT_CMP0148=OLD
        -DPYTHON_EXECUTABLE=${Python_EXECUTABLE}
        "-DPYTHON_INCLUDE_DIR=${PYTHON_REAL_INCLUDE_DIR}"
        "-DPYTHON_INCLUDE_DIRS=${PYTHON_REAL_INCLUDE_DIR}"
        "-DPYTHON_LIBRARY=${PYTHON_REAL_LIBRARY}"
        "-DPYTHON_LIBRARIES=${PYTHON_REAL_LIBRARY}"
        -DGR_PYTHON_DIR=${SP_DIR}
        -DENABLE_PYTHON=ON
        
        # BOOST OVERRIDES
        -DBoost_DIR=${CLEAN_WHEEL_PREFIX}/lib/cmake/Boost-1.82.0
        -DBOOST_ROOT=${CLEAN_WHEEL_PREFIX}
        -DBoost_INCLUDE_DIR=${CLEAN_WHEEL_PREFIX}/include
        -DBoost_LIBRARY_DIR=${CLEAN_WHEEL_PREFIX}/lib
        -DBoost_NO_SYSTEM_PATHS=ON
        -DCMAKE_POLICY_DEFAULT_CMP0144=NEW
        -DCMAKE_POLICY_DEFAULT_CMP0167=OLD
        
        # RUNTIME AUDIO SETUP
        -DENABLE_GNURADIO_RUNTIME=ON
        -DENABLE_GR_AUDIO=ON
        -DAUDIO_BACKEND=${AUDIO_BACKEND}
        "-DPython_NumPy_INCLUDE_DIR=${CLEAN_NUMPY_INCLUDE_DIR}"
        -DCMAKE_POLICY_DEFAULT_CMP0127=OLD
        "-DFFTW3f_INCLUDE_DIRS=${CLEAN_WHEEL_PREFIX}/include"
        "-DFFTW3f_LIBRARIES=${CLEAN_WHEEL_PREFIX}/lib/fftw3f.lib"
        "-DSNDFILE_INCLUDE_DIRS=${CLEAN_WHEEL_PREFIX}/include"
        "-DSNDFILE_LIBRARIES=${CLEAN_WHEEL_PREFIX}/lib/sndfile.lib"
        "-DCMAKE_PROJECT_gnuradio_INCLUDE_BEFORE=${CMAKE_CURRENT_LIST_DIR}/mpir_bridge.cmake"
    
        # --- PORTABLE ISOLATED MULTI-PRECISION MATH TARGETS ---
        -DGMP_INCLUDE_DIR=${GMP_INC_DIR}
        -DGMP_LIBRARY=${GMP_LIB_PATH}
        -DGMPXX_LIBRARY=${GMPXX_LIB_PATH}
        -DMPIR_INCLUDE_DIR=${GMP_INC_DIR}
        -DMPIR_LIBRARY=${GMP_LIB_PATH}
        -DMPIRXX_LIBRARY=${GMPXX_LIB_PATH}
        -DMPLIB_FOUND=TRUE
        -DMPLIB_LIBRARIES=${GMP_LIB_PATH}
    )
    
    ExternalProject_Add(
        gnuradio
        DEPENDS libsndfile_ext volk_ext boost_ext spdlog_ext fftw3f_ext gmp_ext
        GIT_REPOSITORY https://github.com/gnuradio/gnuradio.git
        GIT_TAG v3.10.12.0
        SOURCE_DIR ${CMAKE_BINARY_DIR}/gnuradio-src
        BINARY_DIR ${CMAKE_BINARY_DIR}/gnuradio-build
    
        # Patch command works correctly in-place on the checked out git files
        PATCH_COMMAND ${CMAKE_COMMAND} -E echo "Patching .rc files for winres.h..."
              COMMAND ${CMAKE_COMMAND} -DSOURCE_DIR=${CMAKE_BINARY_DIR}/gnuradio-src -P "${CMAKE_CURRENT_LIST_DIR}/patch_rc.cmake"
        
        CMAKE_ARGS ${GR_CMAKE_ARGS}
        
        BUILD_COMMAND ${CMAKE_COMMAND} --build <BINARY_DIR> --config Release
        INSTALL_COMMAND ${CMAKE_COMMAND} --build <BINARY_DIR> --config Release --target install
        
        # --- RUN THE GENERATED PORTABLE SCRIPT ---
        COMMAND ${Python_EXECUTABLE} "${STUBGEN_SCRIPT}"
    )
endif()
