cmake_minimum_required(VERSION 3.22)
project(AudioPipelineVstHost VERSION 1.0.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ── JUCE ──────────────────────────────────────────────────────────────────────
# Set JUCE_PATH to your JUCE installation, e.g.:
#   cmake -DJUCE_PATH=C:/JUCE ...
if(NOT DEFINED JUCE_PATH)
    set(JUCE_PATH "C:/JUCE" CACHE PATH "Path to JUCE framework")
endif()

if(NOT EXISTS "${JUCE_PATH}/CMakeLists.txt")
    message(FATAL_ERROR
        "JUCE not found at ${JUCE_PATH}.\n"
        "Download JUCE 7 from https://juce.com/get-juce/ and set -DJUCE_PATH=<path>")
endif()

add_subdirectory(${JUCE_PATH} JUCE EXCLUDE_FROM_ALL)

# ── cpp-httplib (header-only, bundled) ────────────────────────────────────────
include(FetchContent)
FetchContent_Declare(
    httplib
    GIT_REPOSITORY https://github.com/yhirose/cpp-httplib.git
    GIT_TAG        v0.15.3
)
FetchContent_MakeAvailable(httplib)

# ── Executable ────────────────────────────────────────────────────────────────
juce_add_console_app(VstHost
    PRODUCT_NAME "AudioPipeline VST Host"
)

target_sources(VstHost PRIVATE
    VstHost.cpp
    RestServer.cpp
)

target_compile_definitions(VstHost PRIVATE
    JUCE_PLUGINHOST_VST3=1
    JUCE_PLUGINHOST_AU=0
    JUCE_WEB_BROWSER=0
    JUCE_USE_CURL=0
)

target_link_libraries(VstHost PRIVATE
    juce::juce_audio_basics
    juce::juce_audio_devices
    juce::juce_audio_formats
    juce::juce_audio_processors
    juce::juce_core
    httplib::httplib
)

if(WIN32)
    target_link_libraries(VstHost PRIVATE ws2_32)
endif()
