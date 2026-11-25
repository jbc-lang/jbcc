package main

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"firebase.google.com/go/v4/auth"
)

type verifyFunc func(context.Context, string) (*auth.Token, error)

func (f verifyFunc) VerifyIDToken(ctx context.Context, token string) (*auth.Token, error) {
	return f(ctx, token)
}

type quotaFunc func(context.Context, string) (func(), time.Duration, error)

func (f quotaFunc) acquire(ctx context.Context, uid string) (func(), time.Duration, error) {
	return f(ctx, uid)
}

func TestProductionCompileGate(t *testing.T) {
	for _, tc := range []struct {
		name, bearer, provider, github string
		verifyError                    bool
		quotaError                     error
		status                         int
	}{
		{name: "anonymous", status: 401},
		{name: "expired", bearer: "expired", verifyError: true, status: 401},
		{name: "wrong provider", bearer: "id-token", provider: "password", github: "123", status: 403},
		{name: "uninvited", bearer: "id-token", provider: "github.com", github: "456", status: 403},
		{name: "allowlisted", bearer: "id-token", provider: "github.com", github: "123", status: 200},
		{name: "rate limited", bearer: "id-token", provider: "github.com", github: "123", quotaError: errLimited, status: 429},
		{name: "quota unavailable", bearer: "id-token", provider: "github.com", github: "123", quotaError: errors.New("unavailable"), status: 503},
	} {
		t.Run(tc.name, func(t *testing.T) {
			worker := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				if tc.status != 200 {
					t.Error("denied request reached the worker")
				}
				if r.Header.Get("Authorization") != "" {
					t.Error("Firebase token was forwarded to the worker")
				}
				send(w, 200, buildResult{})
			}))
			defer worker.Close()

			s := webServer{
				worker: worker.URL, client: worker.Client(), enabled: true,
				access: &accessPolicy{
					allowed: map[string]bool{"123": true},
					verifier: verifyFunc(func(_ context.Context, token string) (*auth.Token, error) {
						if token != tc.bearer {
							t.Errorf("unexpected token %q", token)
						}
						if tc.verifyError {
							return nil, errors.New("expired")
						}
						return &auth.Token{
							UID: "user-123",
							Firebase: auth.FirebaseInfo{
								SignInProvider: tc.provider,
								Identities:     map[string]any{"github.com": []any{tc.github}},
							},
						}, nil
					}),
				},
				quota: quotaFunc(func(_ context.Context, uid string) (func(), time.Duration, error) {
					if uid != "user-123" {
						t.Errorf("quota must use the verified Firebase UID, got %q", uid)
					}
					if tc.status < 429 && tc.status != 200 {
						t.Error("unauthorized request was counted in quota")
					}
					return func() {}, 2500 * time.Millisecond, tc.quotaError
				}),
			}
			r := httptest.NewRequest(http.MethodPost, "/api/v1/compile", strings.NewReader("{}"))
			r.Header.Set("Content-Type", "application/json")
			if tc.bearer != "" {
				r.Header.Set("Authorization", "Bearer "+tc.bearer)
			}
			reply := httptest.NewRecorder()
			s.compile(reply, r)
			if reply.Code != tc.status {
				t.Fatalf("got %d, want %d (%s)", reply.Code, tc.status, reply.Body)
			}
			if tc.status == 429 && reply.Header().Get("Retry-After") != "3" {
				t.Errorf("expected a Retry-After of 3 seconds, got %q", reply.Header().Get("Retry-After"))
			}
		})
	}
}

func TestCloudRunRejectsLocalMode(t *testing.T) {
	t.Setenv("JBCC_MODE", "local")
	t.Setenv("JBCC_WORKER_URL", "http://localhost:8080")
	t.Setenv("K_SERVICE", "compiler")
	if _, err := makeWebServer(context.Background()); err == nil {
		t.Fatal("Cloud Run accepted local mode")
	}
}

func TestBuildHistorySlidingWindowAndLease(t *testing.T) {
	var history buildHistory
	start := time.Now()
	if _, err := history.reserve(start, "first"); err != nil {
		t.Fatal(err)
	}
	if delay, err := history.reserve(start.Add(time.Second), "overlap"); !errors.Is(err, errLimited) || delay != 24*time.Second {
		t.Fatalf("lease overlap returned %s, %v", delay, err)
	}
	for i := 1; i < maxBuildsPerWindow; i++ {
		history.Lease = ""
		if _, err := history.reserve(start.Add(time.Duration(i)*time.Second), "next"); err != nil {
			t.Fatal(err)
		}
	}
	history.Lease = ""
	if delay, err := history.reserve(start.Add(58*time.Second), "limited"); !errors.Is(err, errLimited) || delay != 2*time.Second {
		t.Fatalf("rate limit returned %s, %v", delay, err)
	}
	if _, err := history.reserve(start.Add(time.Minute), "recovered"); err != nil || len(history.Recent) != maxBuildsPerWindow {
		t.Fatalf("window did not recover: %v (%d starts)", err, len(history.Recent))
	}
	if _, err := history.reserve(start.Add(time.Minute+leaseDuration), "after-crash"); err != nil {
		t.Fatalf("expired lease did not recover: %v", err)
	}
}

func TestCloudSavesRequireAnInvite(t *testing.T) {
	s := webServer{
		access: &accessPolicy{
			allowed: map[string]bool{"123": true},
			verifier: verifyFunc(func(context.Context, string) (*auth.Token, error) {
				return &auth.Token{
					UID: "uninvited-user",
					Firebase: auth.FirebaseInfo{
						SignInProvider: "github.com",
						Identities:     map[string]any{"github.com": []any{"456"}},
					},
				}, nil
			}),
		},
	}
	for _, route := range []struct{ method, id string }{
		{http.MethodGet, ""},
		{http.MethodGet, "draft"},
		{http.MethodPut, "draft"},
	} {
		path := "/api/v1/projects"
		if route.id != "" {
			path += "/" + route.id
		}
		for _, auth := range []struct {
			header string
			want   int
		}{
			{"", http.StatusUnauthorized},
			{"Bearer uninvited", http.StatusForbidden},
		} {
			r := httptest.NewRequest(route.method, path, nil)
			r.Header.Set("Authorization", auth.header)
			r.SetPathValue("id", route.id)
			w := httptest.NewRecorder()
			s.serveProjects(w, r)
			if w.Code != auth.want {
				t.Fatalf("%s %s got %d, want %d", route.method, path, w.Code, auth.want)
			}
		}
	}
}
