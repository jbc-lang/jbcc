* Guide CHANGETIMESTAMP examples:
* Years^Months^Weeks^Days^Hours^Minutes^Seconds^Milliseconds
curr_time = 1358247401.205
adj_array = ''
adj_array<8> = 100
CRT CHANGETIMESTAMP(curr_time, adj_array)
adj_array<8> = ''
adj_array<1> = 100
CRT CHANGETIMESTAMP(curr_time, adj_array)
* A month from 2013-01-31 ends on 2013-02-28 (provisional clamp).
CRT CHANGETIMESTAMP(1359590400, '':@FM:1)
CRT CHANGETIMESTAMP(1359590400, '':@FM:'':@FM:1:@FM:-1:@FM:1:@FM:1:@FM:1:@FM:-1)
CRT CHANGETIMESTAMP(1359590400, -1:@FM:-13)
