EQUATE Base TO 1
Total = 0
$INSERT I_GUARDED
$INSERT I_GUARDED
#ifdef Seen
#ifndef seen
CRT Total, Seen
#end
#else
CRT 'inactive'
#endif
#ifdef Missing
#define Hidden 1
#ifndef AlsoMissing
#else
$INSERT MissingFile
INCORRECT (
#endif
#else
CRT Delta
#endif
#ifdef Hidden
CRT 'hidden'
#endif
