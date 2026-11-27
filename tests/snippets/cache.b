INCLUDE JBC.h
* Guide CachePut, CacheGet and CacheExists examples.
CRT '[': CacheGet('bucket1', 'item1'):']'
CRT CacheExists('bucket1', 'item1')
CachePut('bucket1', 'item1', 'value1')
CRT '[': CacheGet('bucket1', 'item1'):']'
CRT CacheExists('bucket1', 'item1'):CacheExists('bucket2', 'item1')
* Guide CacheStats example (CACHE_SIZE adds the value lengths).
CacheClearAll()
CachePut('bucket1', 'item1', 'value1')
CachePut('bucket1', 'item2', 'value2')
CacheGet('bucket1', 'item1')
CacheGet('bucket1', 'item3')
CRT "CACHE_HITS: " : CacheStats('bucket1', CACHE_HITS)
CRT "CACHE_GETS: " : CacheStats('bucket1', CACHE_GETS)
CRT "CACHE_PUTS: " : CacheStats('bucket1', CACHE_PUTS)
CRT "CACHE_SIZE: " : CacheStats('bucket1', CACHE_SIZE)
CRT "CACHE_NB_ITEMS: " : CacheStats('bucket1', CACHE_NB_ITEMS)
CacheClearStats('bucket1')
CRT CacheStats('bucket1', CACHE_PUTS):CacheStats('bucket1', CACHE_NB_ITEMS)
* Guide CacheKeyList and CacheBucketList examples; TAFC sorts names.
CachePut('bucket0', 'z', 'last')
CachePut('bucket0', 'a', 'first')
keys = CacheKeyList('bucket0', @AM)
CRT 'First name: ':keys<1>
CRT 'Second name: ':keys<2>
buckets = CacheBucketList(@AM)
CRT "First bucket: " : buckets<1>
CRT "Second bucket: " : buckets<2>
* Guide CacheDelete, CacheClear and CacheClearAll examples.
CacheDelete('bucket0', 'a')
CRT CacheKeyList('bucket0', ',')
CachePut('ACCOUNT', 'username', 'customer1')
CRT '[': CacheGet('ACCOUNT', 'username'):']'
CacheClear('ACCOUNT')
CRT '[': CacheGet('ACCOUNT', 'username'):']':CacheStats('ACCOUNT', CACHE_GETS)
* Guide CacheGetOption example: zeros until the bucket exists.
CRT 'CACHE_MAX_SIZE: ': CacheGetOption('bucket9', CACHE_MAX_SIZE)
CachePut('bucket9', 'item1', 'value1')
CRT 'CACHE_MAX_SIZE: ': CacheGetOption('bucket9', CACHE_MAX_SIZE)
CRT 'CACHE_PURGE_THRESHOLD: ': CacheGetOption('bucket9', CACHE_PURGE_THRESHOLD)
* A full bucket drops the least recently used items (provisional).
CacheSetOption('small', CACHE_MAX_SIZE, 10)
CacheSetOption('small', CACHE_PURGE_THRESHOLD, 60)
CachePut('small', 'a', 'aaa')
CachePut('small', 'b', 'bbb')
CacheGet('small', 'a')
CachePut('small', 'c', 'ccc')
CRT CacheKeyList('small', ','):' ':CacheStats('small', CACHE_SIZE)
CacheClearAll()
CRT '[':CacheBucketList(','):']'
