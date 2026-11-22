IDs = 'A':@VM:'B':@SM:'C':@FM:'D'
CRT SPLICE(REUSE(FIELD('prefix.rest','.',1)), '/', IDs)
CRT SPLICE(IDs, '/', REUSE('end'))
CRT SPLICE(SPLICE(REUSE('P'), '/', IDs), ':', REUSE('S'))
CRT SPLICE(REUSE('P'), '-', REUSE('S'))
CRT SPLICE('A':@VM:@VM:'C', '-', REUSE('S'))
CRT SPLICE(REUSE('P'), '', IDs)
CRT IDs
