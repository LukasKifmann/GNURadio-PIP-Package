# mpir_bridge.cmake (Corrected for pip/Windows)

set(WHEEL_INCLUDE_DIR "${CMAKE_INSTALL_PREFIX}/include")
set(WHEEL_LIB_DIR "${CMAKE_INSTALL_PREFIX}/lib")

if(NOT EXISTS "${WHEEL_INCLUDE_DIR}/boost")
    file(MAKE_DIRECTORY "${WHEEL_INCLUDE_DIR}/boost")
endif()

if(NOT EXISTS "${WHEEL_INCLUDE_DIR}/boost/version.hpp")
    file(WRITE "${WHEEL_INCLUDE_DIR}/boost/version.hpp" "
#ifndef BOOST_VERSION_HPP
#define BOOST_VERSION_HPP
#define BOOST_VERSION 108200
#define BOOST_LIB_VERSION \"1_82\"
#endif
")
endif()


# ==============================================================================
# DETAILED INTERCEPT: TARGET INTERFACE PATH BINDING
# ==============================================================================
set(BOOST_COMPONENTS date_time program_options system regex thread atomic chrono)

foreach(comp ${BOOST_COMPONENTS})
    if(NOT TARGET Boost::${comp})
        add_library(Boost::${comp} UNKNOWN IMPORTED GLOBAL)
        
        set(LIB_PATH "${WHEEL_LIB_DIR}/boost_${comp}-vc143-mt-x64-1_82.lib")
        if(NOT EXISTS "${LIB_PATH}")
            set(LIB_PATH "${WHEEL_LIB_DIR}/libboost_${comp}-vc143-mt-x64-1_82.lib")
        endif()

        set_target_properties(Boost::${comp} PROPERTIES
            IMPORTED_LOCATION "${LIB_PATH}"
            INTERFACE_INCLUDE_DIRECTORIES "${WHEEL_INCLUDE_DIR}"
        )
    endif()
endforeach()

set(Boost_FOUND TRUE CACHE BOOL "" FORCE)
foreach(comp ${BOOST_COMPONENTS})
    string(TOUPPER ${comp} UPPERCOMP)
    set(Boost_${UPPERCOMP}_FOUND TRUE CACHE BOOL "" FORCE)
    set(Boost_${UPPERCOMP}_LIBRARY "Boost::${comp}" CACHE STRING "" FORCE)
endforeach()

if(NOT TARGET Boost::unit_test_framework)
    add_library(Boost::unit_test_framework UNKNOWN IMPORTED GLOBAL)
    set_target_properties(Boost::unit_test_framework PROPERTIES
        IMPORTED_LOCATION "${WHEEL_LIB_DIR}/boost_unit_test_framework-vc143-mt-x64-1_82.lib"
        INTERFACE_INCLUDE_DIRECTORIES "${WHEEL_INCLUDE_DIR}"
    )
endif()

set(Boost_UNIT_TEST_FRAMEWORK_FOUND TRUE CACHE BOOL "" FORCE)
set(Boost_UNIT_TEST_FRAMEWORK_LIBRARY "Boost::unit_test_framework" CACHE STRING "" FORCE)

if(MSVC)
    add_compile_definitions(BOOST_ALL_NO_LIB)
    add_compile_definitions(BOOST_ALL_DYN_LINK)
endif()

# PIP SANDBOX FORCED TARGET INTERCEPT: VOLK LINK PATH FIX
if(NOT TARGET Volk::volk)
    message(STATUS "--- [PIP Bridge Engine Intercept] Manually Injecting Volk::volk Target ---")
    get_filename_component(REAL_WHEEL_PREFIX "${CMAKE_INSTALL_PREFIX}" ABSOLUTE)
    add_library(Volk::volk UNKNOWN IMPORTED GLOBAL)
    set_target_properties(Volk::volk PROPERTIES
        IMPORTED_LOCATION "${REAL_WHEEL_PREFIX}/lib/volk.lib"
        INTERFACE_INCLUDE_DIRECTORIES "${REAL_WHEEL_PREFIX}/include"
    )
    set(Volk_FOUND TRUE CACHE BOOL "" FORCE)
    set(VOLK_FOUND TRUE CACHE BOOL "" FORCE)
    set(VOLK_TARGET_AVAILABLE TRUE CACHE BOOL "" FORCE)
endif()

# ==============================================================================
# PORTABLE AFXRES.H PATCH FOR RC.EXE 
# ==============================================================================
# mpir_bridge.cmake
if(WIN32)
    message(STATUS "[PORTABLE PATCH] Generating global afxres.h fallback...")
    
    # Write the file ONCE into the global include directory
    # (Assuming CLEAN_WHEEL_PREFIX is accessible as an environment variable or passed in)
    file(WRITE "$ENV{CLEAN_WHEEL_PREFIX}/include/afxres.h" 
        "// MFC Fallback Wrapper\n#include <winres.h>\n"
    )
endif()