# scripts/patch_rc.cmake
file(GLOB_RECURSE RC_FILES "${SOURCE_DIR}/*.rc")
foreach(RC_FILE ${RC_FILES})
    file(READ "${RC_FILE}" RC_CONTENT)
    # Only write if we actually find the text to prevent unnecessary timestamps updates
    if(RC_CONTENT MATCHES "afxres\\.h")
        string(REPLACE "afxres.h" "winres.h" NEW_RC_CONTENT "${RC_CONTENT}")
        file(WRITE "${RC_FILE}" "${NEW_RC_CONTENT}")
        message(STATUS "Patched: ${RC_FILE}")
    endif()
endforeach()