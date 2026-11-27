* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 4: CacheStats size and XTD.
INCLUDE JBC.h
CachePut('b1', 'k1', 'v')
CRT 'size1 ':CacheStats('b1', CACHE_SIZE)
CachePut('b1', 'k2', 'a much longer value than the first one')
CRT 'size2 ':CacheStats('b1', CACHE_SIZE)
CachePut('b1', 'k2', 'x')
CRT 'size3 ':CacheStats('b1', CACHE_SIZE), ' items ':CacheStats('b1', CACHE_NB_ITEMS)
CRT XTD('FFFFFFFF'), XTD('80000000'), XTD('7FFFFFFF'), XTD('1G')
