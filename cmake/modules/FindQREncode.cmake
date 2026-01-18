# Copyright (c) 2019-2020 The Bitcoin developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

#.rst
# FindQREncode
# -------------
#
# Find the QREncode library. The following
# components are available::
#   qrencode
#
# This will define the following variables::
#
#   QREncode_FOUND - system has QREncode lib
#   QREncode_INCLUDE_DIRS - the QREncode include directories
#   QREncode_LIBRARIES - Libraries needed to use QREncode
#
# And the following imported target::
#
#   QREncode::qrencode

include(BrewHelper)
find_brew_prefix(_QREncode_BREW_HINT qrencode)

find_package(PkgConfig)
pkg_check_modules(PC_QREncode QUIET libqrencode)

find_path(QREncode_INCLUDE_DIR
	NAMES qrencode.h
	HINTS ${_QREncode_BREW_HINT}
	PATHS ${PC_QREncode_INCLUDE_DIRS}
	PATH_SUFFIXES include
)

set(QREncode_INCLUDE_DIRS "${QREncode_INCLUDE_DIR}")
mark_as_advanced(QREncode_INCLUDE_DIR)

# TODO: extract a version number.
# For now qrencode does not provide an easy way to extract a version number.

if(QREncode_INCLUDE_DIR)
	include(ExternalLibraryHelper)
    message(STATUS "Debug: QREncode_INCLUDE_DIR=${QREncode_INCLUDE_DIR}")
	find_component(QREncode qrencode
		NAMES qrencode
		HINTS ${_QREncode_BREW_HINT}
		PATHS ${PC_QREncode_LIBRARY_DIRS}
		INCLUDE_DIRS ${QREncode_INCLUDE_DIRS}
	)
    
    if(NOT QREncode_qrencode_LIBRARY)
        message(STATUS "Debug: Primary search failed, trying fallback for libqrencode.dll.a")
        find_library(QREncode_qrencode_LIBRARY_FALLBACK
            NAMES libqrencode.dll.a
            HINTS ${QREncode_INCLUDE_DIR}/../lib
        )
        if(QREncode_qrencode_LIBRARY_FALLBACK)
             message(STATUS "Debug: Found fallback library: ${QREncode_qrencode_LIBRARY_FALLBACK}")
             set(QREncode_qrencode_LIBRARY "${QREncode_qrencode_LIBRARY_FALLBACK}" CACHE FILEPATH "Path to qrencode library" FORCE)
             set(QREncode_qrencode_FOUND TRUE)
             
             if(NOT TARGET QREncode::qrencode)
                add_library(QREncode::qrencode UNKNOWN IMPORTED)
                set_target_properties(QREncode::qrencode PROPERTIES
                    IMPORTED_LOCATION "${QREncode_qrencode_LIBRARY}"
                )
                set_property(TARGET QREncode::qrencode PROPERTY
                    INTERFACE_INCLUDE_DIRECTORIES ${QREncode_INCLUDE_DIRS}
                )
             endif()
        else()
             message(STATUS "Debug: Fallback search failed for libqrencode.dll.a in ${QREncode_INCLUDE_DIR}/../lib")
        endif()
    endif()

    message(STATUS "Debug: QREncode_qrencode_LIBRARY=${QREncode_qrencode_LIBRARY}")
    if(TARGET QREncode::qrencode)
        message(STATUS "Debug: Target QREncode::qrencode exists")
    else()
        message(STATUS "Debug: Target QREncode::qrencode DOES NOT EXIST")
    endif()
endif()

include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(QREncode
	REQUIRED_VARS
		QREncode_INCLUDE_DIR
	HANDLE_COMPONENTS
)
