# Install script for directory: C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-install")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "Release")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

# Set path to fallback-tool for dependency-resolution.
if(NOT DEFINED CMAKE_OBJDUMP)
  set(CMAKE_OBJDUMP "C:/Strawberry/c/bin/objdump.exe")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "lib" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib" TYPE STATIC_LIBRARY FILES "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-build/lib/libevent_core.a")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-install/lib/pkgconfig/libevent_core.pc")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-install/lib/pkgconfig" TYPE FILE FILES "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-build/libevent_core.pc")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "lib" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib" TYPE STATIC_LIBRARY FILES "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-build/lib/libevent_extra.a")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-install/lib/pkgconfig/libevent_extra.pc")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-install/lib/pkgconfig" TYPE FILE FILES "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-build/libevent_extra.pc")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "lib" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib" TYPE STATIC_LIBRARY FILES "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-build/lib/libevent.a")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-install/lib/pkgconfig/libevent.pc")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-install/lib/pkgconfig" TYPE FILE FILES "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-build/libevent.pc")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "dev" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include" TYPE FILE FILES
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/evdns.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/evrpc.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/evhttp.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/evutil.h"
    )
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "dev" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/event2" TYPE FILE FILES
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/buffer.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/bufferevent.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/bufferevent_compat.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/bufferevent_struct.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/buffer_compat.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/dns.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/dns_compat.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/dns_struct.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/event.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/event_compat.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/event_struct.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/http.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/http_compat.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/http_struct.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/keyvalq_struct.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/listener.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/rpc.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/rpc_compat.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/rpc_struct.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/tag.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/tag_compat.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/thread.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/util.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/include/event2/visibility.h"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-build/include/event2/event-config.h"
    )
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "dev" OR NOT CMAKE_INSTALL_COMPONENT)
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-install/lib/cmake/libevent/LibeventConfig.cmake;C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-install/lib/cmake/libevent/LibeventConfigVersion.cmake")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-install/lib/cmake/libevent" TYPE FILE FILES
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-build//CMakeFiles/LibeventConfig.cmake"
    "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-build/LibeventConfigVersion.cmake"
    )
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "dev" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-install/lib/cmake/libevent/LibeventTargets-static.cmake")
    file(DIFFERENT _cmake_export_file_changed FILES
         "$ENV{DESTDIR}C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-install/lib/cmake/libevent/LibeventTargets-static.cmake"
         "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-build/CMakeFiles/Export/4bd69ac1d0116d7da2e1fdfd86d908e8/LibeventTargets-static.cmake")
    if(_cmake_export_file_changed)
      file(GLOB _cmake_old_config_files "$ENV{DESTDIR}C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-install/lib/cmake/libevent/LibeventTargets-static-*.cmake")
      if(_cmake_old_config_files)
        string(REPLACE ";" ", " _cmake_old_config_files_text "${_cmake_old_config_files}")
        message(STATUS "Old export file \"$ENV{DESTDIR}C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-install/lib/cmake/libevent/LibeventTargets-static.cmake\" will be replaced.  Removing files [${_cmake_old_config_files_text}].")
        unset(_cmake_old_config_files_text)
        file(REMOVE ${_cmake_old_config_files})
      endif()
      unset(_cmake_old_config_files)
    endif()
    unset(_cmake_export_file_changed)
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-install/lib/cmake/libevent/LibeventTargets-static.cmake")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-install/lib/cmake/libevent" TYPE FILE FILES "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-build/CMakeFiles/Export/4bd69ac1d0116d7da2e1fdfd86d908e8/LibeventTargets-static.cmake")
  if(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Rr][Ee][Ll][Ee][Aa][Ss][Ee])$")
    list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
     "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-install/lib/cmake/libevent/LibeventTargets-static-release.cmake")
    if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    file(INSTALL DESTINATION "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-install/lib/cmake/libevent" TYPE FILE FILES "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-build/CMakeFiles/Export/4bd69ac1d0116d7da2e1fdfd86d908e8/LibeventTargets-static-release.cmake")
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "runtime" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/bin" TYPE PROGRAM FILES "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-2.1.12-stable/event_rpcgen.py")
endif()

string(REPLACE ";" "\n" CMAKE_INSTALL_MANIFEST_CONTENT
       "${CMAKE_INSTALL_MANIFEST_FILES}")
if(CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-build/install_local_manifest.txt"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
if(CMAKE_INSTALL_COMPONENT)
  if(CMAKE_INSTALL_COMPONENT MATCHES "^[a-zA-Z0-9_.+-]+$")
    set(CMAKE_INSTALL_MANIFEST "install_manifest_${CMAKE_INSTALL_COMPONENT}.txt")
  else()
    string(MD5 CMAKE_INST_COMP_HASH "${CMAKE_INSTALL_COMPONENT}")
    set(CMAKE_INSTALL_MANIFEST "install_manifest_${CMAKE_INST_COMP_HASH}.txt")
    unset(CMAKE_INST_COMP_HASH)
  endif()
else()
  set(CMAKE_INSTALL_MANIFEST "install_manifest.txt")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "C:/Users/donma/OneDrive/Desktop/Radiant-Core/libevent-build/${CMAKE_INSTALL_MANIFEST}"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
