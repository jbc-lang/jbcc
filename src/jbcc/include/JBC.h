* jbcc's built-in JBC.h: the constants that the jBC Programmers Reference
* Guide's examples use (https://jbc-lang.org/). It is not the jBASE header.
* jbcc uses it only when no JBC.h is found on the include paths, and says
* so on stderr; pass --no-builtin-includes to turn it off. The values are
* those of TAFC PB201214's JBC.h (the non-Windows definitions).
*
* Directory delimiter
    EQUATE DIR_DELIM_CH TO "/"
*
* ENCRYPT and DECRYPT methods; the BASE64 forms add XTD(40000000)
    EQUATE JBASE_CRYPT_ROT13 TO 1
    EQUATE JBASE_CRYPT_XOR11 TO 2
    EQUATE JBASE_CRYPT_BLOWFISH_BASE64 TO 1073741831
    EQUATE JBASE_SECUREHASH_SHA256_BASE64 TO 1073741856
*
* IOCTL commands
    EQUATE JIOCTL_COMMAND_CONVERT TO 9
    EQUATE JIOCTL_COMMAND_FILESTATUS TO 10
    EQUATE JIOCTL_COMMAND_FINDRECORD TO 11
    EQUATE JIOCTL_COMMAND_HASH_RECORD TO 15
    EQUATE JIOCTL_COMMAND_FINDRECORD_EXTENDED TO 24
    EQUATE JIOCTL_COMMAND_SEQ_CHANGE_RECORDSIZE TO 62
    EQUATE JBC_COMMAND_GETFILENAME TO 100
*
* User record attributes (SYSTEM(1027) user information)
    EQUATE USER_PROC_PORT_NUMBER TO 1
    EQUATE USER_PROC_ACCOUNT TO 5
    EQUATE USER_PROC_STATS_READ TO 19
    EQUATE USER_PROC_USER_ROOT TO 28
*
* Cache options (CacheGetOption, CacheSetOption) and statistics (CacheStats)
    EQUATE CACHE_MAX_SIZE TO 1
    EQUATE CACHE_PURGE_THRESHOLD TO 2
    EQUATE CACHE_HITS TO 1
    EQUATE CACHE_GETS TO 2
    EQUATE CACHE_PUTS TO 3
    EQUATE CACHE_SIZE TO 4
    EQUATE CACHE_NB_ITEMS TO 5
*
* Logger levels
    EQUATE TAFC_LOG_INFO TO 0
    EQUATE TAFC_LOG_WARNING TO 1
    EQUATE TAFC_LOG_ERROR TO 2
