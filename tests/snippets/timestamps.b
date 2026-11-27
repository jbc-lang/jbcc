* MAKETIMESTAMP, LOCALDATE, LOCALTIME and TIMEDIFF as T24 R19 uses them for
* UTC and server-zone times; dates and times follow the guide's LOCALTIME
* example.
a_date = ICONV('20231031', 'D')
a_time = ICONV('12:34:56', 'MTS')
ts = MAKETIMESTAMP(a_date, a_time, 'UTC')
CRT ts
CRT OCONV(LOCALDATE(ts, 'UTC'), 'D4/E'), OCONV(LOCALTIME(ts, 'UTC'), 'MTS')
CRT OCONV(LOCALDATE(ts, 'Asia/Tokyo'), 'D4/E'), OCONV(LOCALTIME(ts, 'Asia/Tokyo'), 'MTS')
CRT OCONV(LOCALDATE(ts + 43200, 'Asia/Tokyo'), 'D4/E'), OCONV(LOCALTIME(ts + 43200, 'Asia/Tokyo'), 'MTS')
CRT MAKETIMESTAMP(a_date, a_time, 'Asia/Tokyo')
CRT MAKETIMESTAMP(732, 0.5, 'UTC'), MAKETIMESTAMP(731, 86399, 'UTC'), LOCALDATE(-1, 'UTC'), LOCALTIME(-0.5, 'UTC')
d = TIMEDIFF(MAKETIMESTAMP(a_date, a_time, 'Asia/Tokyo'), ts, 0)
CRT CHANGE(d, @FM, '^')
CRT CHANGE(TIMEDIFF(ts + 1000000.25, ts, 1), @FM, '^')
CRT CHANGE(TIMEDIFF(ts, ts + 90, ''), @FM, '^')
