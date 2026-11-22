T = ''
T<1> = 'a:b:c:d:e:f'
T<2> = 'aa:bb:cc:dd:ee:ff':@VM:'1:2:3:4':@SM:':W:X:Y:Z'
T<3> = 'aaa:bbb:ccc:ddd:eee:fff':@VM:@SM
T<4> = 'aaaa:bbbb:cccc:dddd:eeee:ffff'
CRT FIELDS(T, ':', 2)
CRT FIELDS(T, ':', 2, 3)
CRT FIELDS(T, 'bb', 1, 1)
CRT FIELDS(@SM:'x--y':@FM:@VM, '--', 2)
CRT FIELDS('left':@VM:'right', '', 1)
CRT FIELDS('left':@VM:'right', '', 2)
