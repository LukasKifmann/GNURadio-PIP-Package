# pip_deps_injection.cmake
message(STATUS "--- [Pip Injection Layer Engine Triggered] ---")

# Define the absolute workspace directory safely
get_filename_component(REAL_WHEEL_PREFIX "${CMAKE_INSTALL_PREFIX}" ABSOLUTE)

# Manually create the real Volk target inside the inner project context
if(NOT TARGET Volk::volk)
    add_library(Volk::volk UNKNOWN IMPORTED GLOBAL)
    set_target_properties(Volk::volk PROPERTIES
        IMPORTED_LOCATION "${REAL_WHEEL_PREFIX}/lib/volk.lib"
        INTERFACE_INCLUDE_DIRECTORIES "${REAL_WHEEL_PREFIX}/include"
    )
    set(Volk_FOUND TRUE CACHE BOOL "" FORCE)
    set(VOLK_FOUND TRUE CACHE BOOL "" FORCE)
    message(STATUS "--> Successfully forced Volk::volk target redirection to: ${REAL_WHEEL_PREFIX}/lib/volk.lib")
endif()