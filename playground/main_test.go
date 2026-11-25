package main

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
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

func TestCompilePausePreventsWorkerRequests(t *testing.T) {
	var calls atomic.Int32
	worker := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost || r.URL.Path != "/compile" {
			t.Errorf("unexpected worker request %s %s", r.Method, r.URL.Path)
		}
		calls.Add(1)
		send(w, http.StatusOK, buildResult{Diagnostics: []diagnostic{}})
	}))
	defer worker.Close()

	for _, test := range []struct {
		enabled bool
		status  int
		calls   int32
	}{
		{false, http.StatusServiceUnavailable, 0},
		{true, http.StatusOK, 1},
	} {
		request := httptest.NewRequest(http.MethodPost, "/api/v1/compile", strings.NewReader("{}"))
		request.Header.Set("Content-Type", "application/json")
		response := httptest.NewRecorder()
		compileHandler(worker.URL, test.enabled).ServeHTTP(response, request)
		if response.Code != test.status || calls.Load() != test.calls {
			t.Fatalf("enabled=%t: status=%d, worker calls=%d", test.enabled, response.Code, calls.Load())
		}
	}
}
