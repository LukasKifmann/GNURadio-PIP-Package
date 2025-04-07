cmake_minimum_required(VERSION 3.18)
project(gnuradio-local)

include(ExternalProject)

execute_process(COMMAND python3 -c "import sys; print(sys.executable)"
                OUTPUT_VARIABLE PYTHON_EXECUTABLE OUTPUT_STRIP_TRAILING_WHITESPACE)

execute_process(COMMAND python3 -c "import site; print(site.getsitepackages()[0])"
                OUTPUT_VARIABLE SP_DIR OUTPUT_STRIP_TRAILING_WHITESPACE)
                
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
    -DGR_PYTHON_DIR=${SP_DIR}
    -DENABLE_PYTHON=ON
)