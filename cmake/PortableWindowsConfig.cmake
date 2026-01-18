# Portable Windows CMake configuration for Radiant Core
# This script automatically finds dependencies on Windows

cmake_minimum_required(VERSION 3.22)

# Function to find OpenSSL on Windows
function(find_portable_openssl)
    set(OPENSSL_FOUND FALSE)
    
    # Try vcpkg first
    if(DEFINED ENV{VCPKG_ROOT})
        set(VCPKG_OPENSSL "$ENV{VCPKG_ROOT}/installed/x64-windows")
        if(EXISTS "${VCPKG_OPENSSL}/include/openssl/ssl.h")
            set(OPENSSL_ROOT_DIR "${VCPKG_OPENSSL}" CACHE PATH "OpenSSL root directory")
            set(OPENSSL_FOUND TRUE)
            message(STATUS "Found OpenSSL via vcpkg: ${OPENSSL_ROOT_DIR}")
        endif()
    endif()
    
    # Try MSYS2
    if(NOT OPENSSL_FOUND)
        if(EXISTS "C:/msys64_real/mingw64")
             set(MSYS_PREFIX "C:/msys64_real/mingw64")
        elseif(EXISTS "C:/msys64/mingw64")
             set(MSYS_PREFIX "C:/msys64/mingw64")
        endif()

        if(DEFINED MSYS_PREFIX AND EXISTS "${MSYS_PREFIX}/include/openssl/ssl.h")
            set(OPENSSL_ROOT_DIR "${MSYS_PREFIX}" CACHE PATH "OpenSSL root directory")
            set(OPENSSL_FOUND TRUE)
            message(STATUS "Found OpenSSL via MSYS2: ${OPENSSL_ROOT_DIR}")
        endif()
    endif()
    
    # Try Strawberry Perl
    if(NOT OPENSSL_FOUND AND EXISTS "C:/Strawberry/c")
        if(EXISTS "C:/Strawberry/c/include/openssl/ssl.h")
            set(OPENSSL_ROOT_DIR "C:/Strawberry/c" CACHE PATH "OpenSSL root directory")
            set(OPENSSL_FOUND TRUE)
            message(STATUS "Found OpenSSL via Strawberry Perl: ${OPENSSL_ROOT_DIR}")
        endif()
    endif()
    
    # Try system paths
    if(NOT OPENSSL_FOUND)
        set(SYSTEM_PATHS
            "C:/Program Files/OpenSSL"
            "C:/Program Files (x86)/OpenSSL"
            "C:/OpenSSL"
            "C:/OpenSSL-Win64"
        )
        foreach(PATH ${SYSTEM_PATHS})
            if(EXISTS "${PATH}/include/openssl/ssl.h")
                set(OPENSSL_ROOT_DIR "${PATH}" CACHE PATH "OpenSSL root directory")
                set(OPENSSL_FOUND TRUE)
                message(STATUS "Found OpenSSL in system path: ${OPENSSL_ROOT_DIR}")
                break()
            endif()
        endforeach()
    endif()
    
    if(OPENSSL_FOUND)
        # Set the required CMake variables
        set(OPENSSL_INCLUDE_DIR "${OPENSSL_ROOT_DIR}/include" CACHE PATH "OpenSSL include directory")
        set(OPENSSL_CRYPTO_LIBRARY "${OPENSSL_ROOT_DIR}/lib/libcrypto.a" CACHE PATH "OpenSSL crypto library")
        set(OPENSSL_SSL_LIBRARY "${OPENSSL_ROOT_DIR}/lib/libssl.a" CACHE PATH "OpenSSL SSL library")
        
        # Also try .dll files if .a files don't exist
        if(NOT EXISTS "${OPENSSL_CRYPTO_LIBRARY}")
            set(OPENSSL_CRYPTO_LIBRARY "${OPENSSL_ROOT_DIR}/lib/libcrypto.dll.a" CACHE PATH "OpenSSL crypto library")
        endif()
        if(NOT EXISTS "${OPENSSL_SSL_LIBRARY}")
            set(OPENSSL_SSL_LIBRARY "${OPENSSL_ROOT_DIR}/lib/libssl.dll.a" CACHE PATH "OpenSSL SSL library")
        endif()
        
        message(STATUS "OpenSSL libraries: ${OPENSSL_CRYPTO_LIBRARY}, ${OPENSSL_SSL_LIBRARY}")
    else()
        message(FATAL_ERROR "OpenSSL not found. Please install OpenSSL via vcpkg, MSYS2, or Strawberry Perl")
    endif()
endfunction()

# Function to find Boost on Windows
function(find_portable_boost)
    # Try bundled boost first
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/boost-1.83.0")
        set(BOOST_INCLUDEDIR "${CMAKE_CURRENT_SOURCE_DIR}/boost-1.83.0" CACHE PATH "Boost include directory")
        set(BOOST_LIBRARYDIR "${CMAKE_CURRENT_SOURCE_DIR}/boost-1.83.0/stage/lib" CACHE PATH "Boost library directory")
        message(STATUS "Using bundled Boost: ${BOOST_INCLUDEDIR}")
        return()
    endif()
    
    # Try vcpkg
    if(DEFINED ENV{VCPKG_ROOT})
        set(BOOST_INCLUDEDIR "$ENV{VCPKG_ROOT}/installed/x64-windows/include" CACHE PATH "Boost include directory")
        set(BOOST_LIBRARYDIR "$ENV{VCPKG_ROOT}/installed/x64-windows/lib" CACHE PATH "Boost library directory")
        message(STATUS "Found Boost via vcpkg: ${BOOST_INCLUDEDIR}")
        return()
    endif()
    
    # Try MSYS2
    if(EXISTS "C:/msys64/mingw64")
        set(BOOST_INCLUDEDIR "C:/msys64/mingw64/include" CACHE PATH "Boost include directory")
        set(BOOST_LIBRARYDIR "C:/msys64/mingw64/lib" CACHE PATH "Boost library directory")
        message(STATUS "Found Boost via MSYS2: ${BOOST_INCLUDEDIR}")
        return()
    endif()
    
    # Try system paths
    find_path(BOOST_ROOT
        NAMES boost/version.hpp
        PATHS
            "C:/local/boost_*"
            "C:/boost"
            "C:/Program Files/boost"
            "C:/Program Files (x86)/boost"
        DOC "Boost root directory"
    )
    
    if(BOOST_ROOT)
        set(BOOST_INCLUDEDIR "${BOOST_ROOT}" CACHE PATH "Boost include directory")
        set(BOOST_LIBRARYDIR "${BOOST_ROOT}/lib" CACHE PATH "Boost library directory")
        message(STATUS "Found Boost: ${BOOST_ROOT}")
    else()
        message(FATAL_ERROR "Boost not found. Please install Boost via vcpkg, MSYS2, or bundle it with the source")
    endif()
endfunction()

# Function to find libevent on Windows
# Priority: vcpkg > MSYS2 > bundled (real) > stubs (last resort)
function(find_portable_libevent)
    set(LIBEVENT_FOUND FALSE PARENT_SCOPE)
    
    # Try vcpkg first (preferred for proper Windows builds)
    if(DEFINED ENV{VCPKG_ROOT})
        set(_vcpkg_libevent "$ENV{VCPKG_ROOT}/installed/x64-windows")
        if(EXISTS "${_vcpkg_libevent}/include/event2/event.h")
            set(Event_INCLUDE_DIR "${_vcpkg_libevent}/include" CACHE PATH "libevent include directory")
            set(Event_event_LIBRARY "${_vcpkg_libevent}/lib/event.lib" CACHE FILEPATH "libevent library")
            if(NOT EXISTS "${Event_event_LIBRARY}")
                set(Event_event_LIBRARY "${_vcpkg_libevent}/lib/libevent.a" CACHE FILEPATH "libevent library" FORCE)
            endif()
            set(CMAKE_INCLUDE_PATH "${_vcpkg_libevent}/include" ${CMAKE_INCLUDE_PATH} PARENT_SCOPE)
            set(CMAKE_LIBRARY_PATH "${_vcpkg_libevent}/lib" ${CMAKE_LIBRARY_PATH} PARENT_SCOPE)
            set(LIBEVENT_FOUND TRUE PARENT_SCOPE)
            message(STATUS "Found libevent via vcpkg: ${_vcpkg_libevent}")
            return()
        endif()
    endif()
    
    # Try MSYS2 (good for MinGW builds)
    if(EXISTS "C:/msys64/mingw64/include/event2/event.h")
        set(Event_INCLUDE_DIR "C:/msys64/mingw64/include" CACHE PATH "libevent include directory")
        set(Event_event_LIBRARY "C:/msys64/mingw64/lib/libevent.a" CACHE FILEPATH "libevent library")
        set(CMAKE_INCLUDE_PATH "C:/msys64/mingw64/include" ${CMAKE_INCLUDE_PATH} PARENT_SCOPE)
        set(CMAKE_LIBRARY_PATH "C:/msys64/mingw64/lib" ${CMAKE_LIBRARY_PATH} PARENT_SCOPE)
        set(LIBEVENT_FOUND TRUE PARENT_SCOPE)
        message(STATUS "Found libevent via MSYS2: C:/msys64/mingw64")
        return()
    endif()
    
    # Try bundled libevent (if it's a real build, not stubs)
    set(_bundled_libevent "${CMAKE_CURRENT_SOURCE_DIR}/libevent-install")
    if(EXISTS "${_bundled_libevent}/include/event2/event.h" AND 
       EXISTS "${_bundled_libevent}/lib/libevent.a")
        # Check if it's a real libevent (file size > 100KB indicates real library)
        file(SIZE "${_bundled_libevent}/lib/libevent.a" _libevent_size)
        if(_libevent_size GREATER 100000)
            set(Event_INCLUDE_DIR "${_bundled_libevent}/include" CACHE PATH "libevent include directory")
            set(Event_event_LIBRARY "${_bundled_libevent}/lib/libevent.a" CACHE FILEPATH "libevent library")
            # Set version from bundled build (check pkgconfig or default to 2.1.12)
            if(EXISTS "${_bundled_libevent}/lib/pkgconfig/libevent.pc")
                file(STRINGS "${_bundled_libevent}/lib/pkgconfig/libevent.pc" _pc_version REGEX "^Version:")
                if(_pc_version MATCHES "Version: ([0-9]+\\.[0-9]+\\.[0-9]+)")
                    set(Event_VERSION "${CMAKE_MATCH_1}" CACHE STRING "libevent version")
                endif()
            endif()
            if(NOT Event_VERSION)
                set(Event_VERSION "2.1.12" CACHE STRING "libevent version")
            endif()
            set(CMAKE_INCLUDE_PATH "${_bundled_libevent}/include" ${CMAKE_INCLUDE_PATH} PARENT_SCOPE)
            set(CMAKE_LIBRARY_PATH "${_bundled_libevent}/lib" ${CMAKE_LIBRARY_PATH} PARENT_SCOPE)
            set(LIBEVENT_FOUND TRUE PARENT_SCOPE)
            message(STATUS "Using bundled libevent: ${_bundled_libevent} (version ${Event_VERSION})")
            return()
        else()
            message(WARNING "Bundled libevent appears to be stubs (size: ${_libevent_size} bytes)")
        endif()
    endif()
    
    # Last resort: warn about missing libevent
    message(WARNING "")
    message(WARNING "=============================================================")
    message(WARNING "libevent NOT FOUND - RPC functionality will NOT work!")
    message(WARNING "")
    message(WARNING "Please install libevent via one of:")
    message(WARNING "  - vcpkg: .\\vcpkg install libevent:x64-windows")
    message(WARNING "  - MSYS2: pacman -S mingw-w64-x86_64-libevent")
    message(WARNING "  - WSL2:  sudo apt install libevent-dev")
    message(WARNING "=============================================================")
    message(WARNING "")
endfunction()

# Apply portable configuration
find_portable_openssl()
find_portable_boost()
find_portable_libevent()

# Apply portable configuration for Windows
if(${CMAKE_SYSTEM_NAME} MATCHES "Windows")
    # Use static linking for better portability
    set(CMAKE_FIND_LIBRARY_SUFFIXES ".a" ".lib" ".dll.a")
    
    # Add common Windows flags
    add_compile_definitions(
        WIN32_LEAN_AND_MEAN
        NOMINMAX
        _WIN32_WINNT=0x0601  # Windows 7
    )
    
    # Set Windows SDK paths for MinGW
    if(MINGW)
        if(NOT DEFINED MSYS_PREFIX)
            if(EXISTS "C:/msys64_real/mingw64")
                 set(MSYS_PREFIX "C:/msys64_real/mingw64")
            elseif(EXISTS "C:/msys64/mingw64")
                 set(MSYS_PREFIX "C:/msys64/mingw64")
            endif()
        endif()

        # Add MinGW include paths
        set(CMAKE_SYSTEM_INCLUDE_PATH 
            "${MSYS_PREFIX}/include"
            "C:/Strawberry/c/x86_64-w64-mingw32/include"
            ${CMAKE_SYSTEM_INCLUDE_PATH}
        )
        
        # Add MinGW library paths
        set(CMAKE_SYSTEM_LIBRARY_PATH
            "${MSYS_PREFIX}/lib"
            "C:/Strawberry/c/x86_64-w64-mingw32/lib"
            ${CMAKE_SYSTEM_LIBRARY_PATH}
        )
        
        # Find shlwapi.h in MinGW paths
        find_path(SHLWAPI_INCLUDE_DIR 
            NAMES shlwapi.h
            PATHS 
                "${MSYS_PREFIX}/include"
                "C:/Strawberry/c/x86_64-w64-mingw32/include"
                "C:/msys64/ucrt64/include"
                "C:/msys64_real/ucrt64/include"
        )
        
        if(SHLWAPI_INCLUDE_DIR)
            set(SHLWAPI_INCLUDE_DIRS "${SHLWAPI_INCLUDE_DIR}")
            message(STATUS "Found shlwapi.h at: ${SHLWAPI_INCLUDE_DIR}")
        endif()
        
        # Find Windows libraries
        find_library(WS2_32_LIBRARY
            NAMES ws2_32
            PATHS
                "${MSYS_PREFIX}/lib"
                "C:/Strawberry/c/x86_64-w64-mingw32/lib"
                "${MSYS_PREFIX}/lib/gcc/x86_64-w64-mingw32/13.2.0"
                "${MSYS_PREFIX}/lib/gcc/x86_64-w64-mingw32/15.2.0"
        )
        
        find_library(CRYPT32_LIBRARY
            NAMES crypt32
            PATHS
                "${MSYS_PREFIX}/lib"
        )
        
        if(WS2_32_LIBRARY)
            message(STATUS "Found ws2_32 library: ${WS2_32_LIBRARY}")
            link_libraries(${WS2_32_LIBRARY})
        endif()
        
        if(CRYPT32_LIBRARY)
            message(STATUS "Found crypt32 library: ${CRYPT32_LIBRARY}")
            link_libraries(${CRYPT32_LIBRARY})
        endif()
        
        add_compile_options(-Wno-unused-parameter)
        add_link_options(-static-libgcc -static-libstdc++)
    endif()
    
    # If using MSVC
    if(MSVC)
        add_compile_options(/W3 /MP)
        add_link_options(/INCREMENTAL:NO)
    endif()
endif()

message(STATUS "Portable Windows configuration applied")
