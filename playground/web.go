package main

import (
	"context"
	"encoding/json"
	"errors"
	"log"
	"math"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"

	"cloud.google.com/go/firestore"
	firebase "firebase.google.com/go/v4"
	"google.golang.org/api/idtoken"
)

type browserAuth struct {
	APIKey     string `json:"apiKey"`
	AuthDomain string `json:"authDomain"`
	ProjectID  string `json:"projectId"`
	AppID      string `json:"appId"`
}

type webServer struct {
	origin    string
	worker    string
	client    *http.Client
	enabled   bool
	auth      *browserAuth
	access    *accessPolicy
	quota     buildQuota
	projects  projectStore
	analytics string
}

var authDomain = regexp.MustCompile(`^[a-z0-9-]+\.firebaseapp\.com$`)

func hostOrigin(value string) (*url.URL, error) {
	u, err := url.Parse(value)
	if err != nil || u.Scheme != "https" || u.Host == "" || u.User != nil ||
		u.Path != "" || u.ForceQuery || u.RawQuery != "" || u.Fragment != "" {
		return nil, errors.New("production URLs must be HTTPS origins without a path")
	}
	return u, nil
}

func makeWebServer(ctx context.Context) (*webServer, error) {
	config := &webServer{
		worker: os.Getenv("JBCC_WORKER_URL"), client: http.DefaultClient,
	}
	if config.worker == "" {
		return nil, errors.New("set JBCC_WORKER_URL")
	}
	if analytics := os.Getenv("JBCC_ANALYTICS_ORIGIN"); analytics != "" {
		u, err := hostOrigin(analytics)
		if err != nil || !strings.HasSuffix(u.Hostname(), ".web.app") || u.Port() != "" {
			return nil, errors.New("JBCC_ANALYTICS_ORIGIN must be a Firebase Hosting origin")
		}
		config.analytics = u.String()
	}
	mode := os.Getenv("JBCC_MODE")
	config.enabled = mode == "local"
	if value, set := os.LookupEnv("JBCC_BUILDS_ENABLED"); set {
		var err error
		config.enabled, err = strconv.ParseBool(value)
		if err != nil {
			return nil, errors.New("JBCC_BUILDS_ENABLED must be true or false")
		}
	}
	switch mode {
	case "local":
		if os.Getenv("K_SERVICE") != "" {
			return nil, errors.New("local playground mode is unavailable on Cloud Run")
		}
		return config, nil
	case "production":
		if os.Getenv("FIREBASE_AUTH_EMULATOR_HOST") != "" || os.Getenv("FIRESTORE_EMULATOR_HOST") != "" {
			return nil, errors.New("production cannot use Firebase emulators")
		}
	default:
		return nil, errors.New("set JBCC_MODE to local or production")
	}

	origin, err := hostOrigin(os.Getenv("JBCC_PUBLIC_ORIGIN"))
	if err != nil {
		return nil, errors.New("set JBCC_PUBLIC_ORIGIN to the public HTTPS origin")
	}
	worker, err := hostOrigin(config.worker)
	if err != nil || !strings.HasSuffix(worker.Hostname(), ".run.app") || worker.Port() != "" {
		return nil, errors.New("set JBCC_WORKER_URL to the private Cloud Run service origin")
	}
	config.origin = origin.String()
	if config.analytics != "" && config.analytics == config.origin {
		return nil, errors.New("analytics must use an origin separate from the editor")
	}
	authConfig := &browserAuth{
		APIKey: os.Getenv("JBCC_FIREBASE_API_KEY"), AuthDomain: os.Getenv("JBCC_FIREBASE_AUTH_DOMAIN"),
		ProjectID: os.Getenv("JBCC_FIREBASE_PROJECT"), AppID: os.Getenv("JBCC_FIREBASE_APP_ID"),
	}
	database := os.Getenv("JBCC_FIRESTORE_DATABASE")
	if authConfig.APIKey == "" || authConfig.AppID == "" || authConfig.ProjectID == "" ||
		!authDomain.MatchString(authConfig.AuthDomain) || database == "" {
		return nil, errors.New("production requires Firebase web configuration and JBCC_FIRESTORE_DATABASE")
	}
	allowed, err := githubAllowlist(os.Getenv("JBCC_ALLOWED_GITHUB_IDS"))
	if err != nil {
		return nil, err
	}
	app, err := firebase.NewApp(ctx, &firebase.Config{ProjectID: authConfig.ProjectID})
	if err != nil {
		return nil, err
	}
	verifier, err := app.Auth(ctx)
	if err != nil {
		return nil, err
	}
	db, err := firestore.NewClientWithDatabase(ctx, authConfig.ProjectID, database)
	if err != nil {
		return nil, err
	}
	config.client, err = idtoken.NewClient(ctx, worker.String())
	if err != nil {
		db.Close()
		return nil, err
	}
	config.client.CheckRedirect = func(*http.Request, []*http.Request) error {
		return http.ErrUseLastResponse
	}
	config.auth = authConfig
	config.access = &accessPolicy{verifier: verifier, allowed: allowed}
	config.quota = firestoreQuota{db: db}
	config.projects = firestoreProjects{db: db}
	return config, nil
}

func (s *webServer) sameOrigin(r *http.Request) bool {
	origin := r.Header.Get("Origin")
	if origin == "" {
		return true
	}
	if s.origin == "" {
		return origin == "http://"+r.Host
	}
	return origin == s.origin || origin == "https://"+r.Host && strings.HasSuffix(r.Host, ".run.app")
}

func (s *webServer) compile(w http.ResponseWriter, r *http.Request) {
	if !s.enabled {
		failure(w, http.StatusServiceUnavailable, "playground builds are paused")
		return
	}
	if !s.sameOrigin(r) {
		failure(w, http.StatusForbidden, "expected a same-origin request")
		return
	}
	body, ok := projectBody(w, r)
	if !ok {
		return
	}
	if s.access != nil {
		ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
		uid, ok := s.access.authenticate(w, r.WithContext(ctx))
		if !ok {
			cancel()
			return
		}
		release, delay, err := s.quota.acquire(ctx, uid)
		cancel()
		if errors.Is(err, errLimited) {
			w.Header().Set("Retry-After", strconv.Itoa(max(1, int(math.Ceil(delay.Seconds())))))
			failure(w, http.StatusTooManyRequests, "build quota exceeded. Try again shortly")
			return
		}
		if err != nil {
			log.Printf("could not reserve a build: %v", err)
			failure(w, http.StatusServiceUnavailable, "build quota temporarily unavailable")
			return
		}
		defer release()
	}
	proxyBuild(w, r, s.client, s.worker, body)
}

func (s *webServer) register(mux *http.ServeMux, root string) http.Handler {
	mux.HandleFunc("POST /api/v1/compile", s.compile)
	if s.projects != nil {
		mux.HandleFunc("GET /api/v1/projects", s.serveProjects)
		mux.HandleFunc("GET /api/v1/projects/{id}", s.serveProjects)
		mux.HandleFunc("PUT /api/v1/projects/{id}", s.serveProjects)
	}
	mux.HandleFunc("GET /api/v1/auth/config", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Cache-Control", "no-store")
		_ = json.NewEncoder(w).Encode(s.auth)
	})
	mux.HandleFunc("GET /api/v1/auth/session", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", "no-store")
		if s.access != nil {
			ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
			defer cancel()
			if _, ok := s.access.authenticate(w, r.WithContext(ctx)); !ok {
				return
			}
		}
		w.WriteHeader(http.StatusNoContent)
	})
	mux.HandleFunc("GET /api/v1/analytics", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", "no-store")
		if s.analytics == "" {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		_, _ = w.Write([]byte(s.analytics))
	})
	mux.HandleFunc("GET /runner.html", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Security-Policy", "sandbox allow-scripts; default-src 'none'; script-src 'self' 'wasm-unsafe-eval'; worker-src blob:; frame-ancestors 'self'; base-uri 'none'; form-action 'none'")
		http.ServeFile(w, r, filepath.Join(root, "runner.html"))
	})
	files := http.FileServer(http.Dir(root))
	mux.HandleFunc("GET /", func(w http.ResponseWriter, r *http.Request) {
		csp := "default-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
		frames := "'self'"
		if s.auth != nil {
			csp += "; script-src 'self' https://apis.google.com; connect-src 'self' https://identitytoolkit.googleapis.com https://securetoken.googleapis.com https://apis.google.com"
			frames += " https://" + s.auth.AuthDomain
			w.Header().Set("Cross-Origin-Opener-Policy", "same-origin-allow-popups")
		}
		if s.analytics != "" {
			frames += " " + s.analytics
		}
		w.Header().Set("Content-Security-Policy", csp+"; frame-src "+frames)
		files.ServeHTTP(w, r)
	})
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if s.auth == nil && !localHost(r.Host) {
			failure(w, http.StatusForbidden, "local playground requires a loopback host")
			return
		}
		w.Header().Set("X-Content-Type-Options", "nosniff")
		mux.ServeHTTP(w, r)
	})
}
