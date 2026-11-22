SUBROUTINE GET.STATUS(Rec, Answer)
IF Rec<2> EQ 'ACTIVE' THEN
  Answer = 'open'
END ELSE
  Answer = 'closed'
END
RETURN
END
