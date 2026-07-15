# gmp_bridge.cmake
include(ExternalProject)

# Define an isolated local path inside your build tree
set(GMP_PREFIX "${CMAKE_BINARY_DIR}/deps/gmp")
set(GMP_INCLUDE_DIR "${GMP_PREFIX}/include")

if(WIN32)
    # WINDOWS: Fetch precompiled static libs to bypass needing a full MSYS2 environment
    ExternalProject_Add(gmp_local
        URL "https://github.com/mbuilov/mpir-windows-pm/releases/download/v3.0.0/mpir-3.0.0-vc15-x64-static.zip"
        PREFIX ${GMP_PREFIX}
        CONFIGURE_COMMAND ""
        BUILD_COMMAND ""
        INSTALL_COMMAND ${CMAKE_COMMAND} -E copy_directory <SOURCE_DIR> ${GMP_PREFIX}
    )
    # Match the internal filenames of the prebuilt archive
    set(GMP_LIB_FILE "${GMP_PREFIX}/lib/mpir.lib")
    set(GMPXX_LIB_FILE "${GMP_PREFIX}/lib/mpirxx.lib")
else()
    # UNIX (Linux / macOS): Compile 100% statically from source
    ExternalProject_Add(gmp_local
        URL "https://gmplib.org/download/gmp/gmp-6.3.0.tar.xz"
        PREFIX ${GMP_PREFIX}
        # -fPIC ensures the static library can be cleanly baked into the final wheel/binary
        CONFIGURE_COMMAND <SOURCE_DIR>/configure --prefix=${GMP_PREFIX} --enable-cxx --disable-shared --enable-static CFLAGS=-fPIC CXXFLAGS=-fPIC
        BUILD_COMMAND make -j${PROCESSOR_COUNT}
        INSTALL_COMMAND make install
    )
    set(GMP_LIB_FILE "${GMP_PREFIX}/lib/libgmp.a")
    set(GMPXX_LIB_FILE "${GMP_PREFIX}/lib/libgmpxx.a")
endif()