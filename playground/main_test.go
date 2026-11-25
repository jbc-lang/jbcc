package main

import (
	"context"
	"errors"
	"testing"
	"time"
)

func TestCancelledBuildStopsChildProcess(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 150*time.Millisecond)
	defer cancel()
	start := time.Now()
	_, err := runTool(ctx, t.TempDir(), "sh", "-c", "sleep 30 & wait")
	if err == nil || !errors.Is(ctx.Err(), context.DeadlineExceeded) {
		t.Fatalf("runTool returned %v with context %v", err, ctx.Err())
	}
	if elapsed := time.Since(start); elapsed > time.Second {
		t.Fatalf("child process held open the build pipes for %s", elapsed)
	}
}
