package main

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"io"
	"log"
	"mime"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"syscall"
	"time"
	"unicode/utf8"
)

const (
	requestLimit  = 512 << 10
	artifactLimit = 4 << 20
	responseLimit = 6 << 20
	buildTimeout  = 15 * time.Second
)

type project struct {
	Entry string       `json:"entry" firestore:"entry"`
	Units []string     `json:"units" firestore:"units"`
	Files []sourceFile `json:"files" firestore:"files"`
}

type sourceFile struct {
	Path   string `json:"path" firestore:"path"`
	Source string `json:"source" firestore:"source"`
}

type diagnostic struct {
	Path     string `json:"path,omitempty"`
	Line     int    `json:"line,omitempty"`
	Column   int    `json:"column,omitempty"`
	Severity string `json:"severity"`
	Message  string `json:"message"`
}

type buildResult struct {
	Diagnostics []diagnostic `json:"diagnostics"`
	JavaScript  string       `json:"javascript,omitempty"`
	Wasm        string       `json:"wasm,omitempty"`
}

var (
	pathPart = regexp.MustCompile(`^[a-zA-Z0-9_.-]+$`)
	location = regexp.MustCompile(`^([^:]+):([0-9]+):([0-9]+): (.*)$`)
)

func (p project) validate() (int, string) {
	if len(p.Files) > 32 {
		return 413, "project exceeds 32 files"
	}
	names := make(map[string]bool)
	total := 0
	for _, file := range p.Files {
		if len(file.Path) > 240 || strings.HasPrefix(file.Path, "-") {
			return 400, "invalid project file path"
		}
		for part := range strings.SplitSeq(file.Path, "/") {
			if part == "." || part == ".." || !pathPart.MatchString(part) {
				return 400, "invalid project file path"
			}
		}
		if names[file.Path] {
			return 400, "duplicate project file path"
		}
		names[file.Path] = true
		total += len(file.Source)
		if len(file.Source) > 64<<10 || total > 256<<10 {
			return 413, "source exceeds project size limit"
		}
	}
	for name := range names {
		for dir := filepath.Dir(name); dir != "."; dir = filepath.Dir(dir) {
			if names[dir] {
				return 400, "file path conflicts with a project directory"
			}
		}
	}
	seen := make(map[string]bool)
	for _, unit := range append([]string{p.Entry}, p.Units...) {
		if !names[unit] || seen[unit] {
			return 400, "entry and linked units must name distinct project files"
		}
		seen[unit] = true
	}
	return 0, ""
}

func send(w http.ResponseWriter, status int, result buildResult) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(result)
}

func failure(w http.ResponseWriter, status int, message string) {
	send(w, status, buildResult{Diagnostics: []diagnostic{{Severity: "error", Message: message}}})
}

func projectBody(w http.ResponseWriter, r *http.Request) ([]byte, bool) {
	contentType, _, err := mime.ParseMediaType(r.Header.Get("Content-Type"))
	if err != nil || contentType != "application/json" {
		failure(w, 415, "expected application/json")
		return nil, false
	}
	body, err := io.ReadAll(http.MaxBytesReader(w, r.Body, requestLimit))
	var tooLarge *http.MaxBytesError
	if errors.As(err, &tooLarge) {
		failure(w, 413, "request exceeds 512 KiB")
		return nil, false
	}
	if err != nil || !utf8.Valid(body) {
		failure(w, 400, "expected a UTF-8 JSON request")
		return nil, false
	}
	return body, true
}

func strictJSON(body []byte, value any) bool {
	decoder := json.NewDecoder(bytes.NewReader(body))
	decoder.DisallowUnknownFields()
	return decoder.Decode(value) == nil && decoder.Decode(new(any)) == io.EOF
}

type boundedLog struct {
	bytes.Buffer
}

func (b *boundedLog) Write(p []byte) (int, error) {
	space := (16 << 10) - b.Len()
	b.Buffer.Write(p[:min(len(p), space)])
	return len(p), nil
}

func runTool(ctx context.Context, dir, tool string, args ...string) (string, error) {
	cmd := exec.CommandContext(ctx, tool, args...)
	cmd.Dir = dir
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
	cmd.Cancel = func() error {
		err := syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL)
		if errors.Is(err, syscall.ESRCH) {
			return os.ErrProcessDone
		}
		return err
	}
	cmd.WaitDelay = time.Second
	var output boundedLog
	cmd.Stdout, cmd.Stderr = &output, &output
	err := cmd.Run()
	return output.String(), err
}

func diagnostics(output string) []diagnostic {
	result := []diagnostic{}
	for line := range strings.SplitSeq(strings.TrimSpace(output), "\n") {
		if line == "" {
			continue
		}
		item := diagnostic{Severity: "error", Message: line}
		if parts := location.FindStringSubmatch(line); parts != nil {
			item.Path = parts[1]
			item.Line, _ = strconv.Atoi(parts[2])
			item.Column, _ = strconv.Atoi(parts[3])
			item.Message = parts[4]
		}
		if message, ok := strings.CutPrefix(item.Message, "warning: "); ok {
			item.Severity, item.Message = "warning", message
		}
		result = append(result, item)
	}
	return result
}

func stage(dir string, files []sourceFile) error {
	for _, file := range files {
		path := filepath.Join(dir, file.Path)
		if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
			return err
		}
		if err := os.WriteFile(path, []byte(file.Source), 0600); err != nil {
			return err
		}
	}
	return nil
}

func compile(w http.ResponseWriter, r *http.Request, translator string) {
	body, ok := projectBody(w, r)
	if !ok {
		return
	}
	var p project
	if !strictJSON(body, &p) {
		failure(w, 400, "invalid project request")
		return
	}
	if status, message := p.validate(); status != 0 {
		failure(w, status, message)
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), buildTimeout)
	defer cancel()
	dir, err := os.MkdirTemp("", "jbcc-")
	if err != nil {
		failure(w, 500, "cannot create compiler workspace")
		return
	}
	defer os.RemoveAll(dir)
	sources := filepath.Join(dir, "sources")
	if err := stage(sources, p.Files); err != nil {
		failure(w, 500, "cannot stage project files")
		return
	}
	args := append([]string{translator, "../program.c", p.Entry}, p.Units...)
	output, err := runTool(ctx, sources, "python3", args...)
	if ctx.Err() != nil {
		failure(w, 504, "compilation cancelled or timed out")
		return
	}
	result := buildResult{Diagnostics: diagnostics(output)}
	if err != nil {
		var exit *exec.ExitError
		if !errors.As(err, &exit) || len(result.Diagnostics) == 0 {
			failure(w, 500, "compiler failed")
			return
		}
		status := 422
		if exit.ExitCode() == 2 {
			status = 413
		}
		send(w, status, result)
		return
	}

	output, err = runTool(ctx, dir, "emcc", "program.c", "-std=c99", "-O0",
		"-sMODULARIZE=1", "-sEXPORT_NAME=createProgram", "-sENVIRONMENT=worker",
		"-sEXIT_RUNTIME=1", "-sFORCE_FILESYSTEM=1", "-sALLOW_MEMORY_GROWTH=1", "-sMAXIMUM_MEMORY=64MB",
		"-sINCOMING_MODULE_JS_API=wasmBinary,stdin,stdout,stderr,print,printErr,onExit",
		"-o", "program.js")
	if ctx.Err() != nil {
		failure(w, 504, "compilation cancelled or timed out")
		return
	}
	if err != nil {
		log.Printf("emcc failed: %v\n%s", err, output)
		failure(w, 422, "Emscripten could not build this program")
		return
	}
	var remaining int64 = artifactLimit
	for _, artifact := range []struct {
		name string
		data *string
	}{{"program.js", &result.JavaScript}, {"program.wasm", &result.Wasm}} {
		file, err := os.Open(filepath.Join(dir, artifact.name))
		if err != nil {
			failure(w, 500, "cannot read compiler artifact")
			return
		}
		content, err := io.ReadAll(io.LimitReader(file, remaining+1))
		file.Close()
		if err != nil {
			failure(w, 500, "cannot read compiler artifact")
			return
		}
		remaining -= int64(len(content))
		if remaining < 0 {
			failure(w, 413, "artifacts exceed 4 MiB")
			return
		}
		*artifact.data = base64.StdEncoding.EncodeToString(content)
	}
	send(w, 200, result)
}

func localHost(host string) bool {
	if name, _, err := net.SplitHostPort(host); err == nil {
		host = name
	}
	return host == "127.0.0.1" || host == "localhost" || host == "::1" || host == "[::1]"
}

func proxyBuild(w http.ResponseWriter, r *http.Request, client *http.Client, worker string, body []byte) {
	ctx, cancel := context.WithTimeout(r.Context(), buildTimeout+3*time.Second)
	defer cancel()
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, worker+"/compile", bytes.NewReader(body))
	if err != nil {
		failure(w, 500, "invalid worker configuration")
		return
	}
	request.Header.Set("Content-Type", "application/json")
	response, err := client.Do(request)
	if err != nil {
		if ctx.Err() != nil {
			failure(w, 504, "compilation cancelled or timed out")
		} else {
			failure(w, 502, "compiler worker unavailable")
		}
		return
	}
	defer response.Body.Close()
	result, err := io.ReadAll(io.LimitReader(response.Body, responseLimit+1))
	if err != nil || len(result) > responseLimit {
		failure(w, 502, "invalid compiler worker response")
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	w.WriteHeader(response.StatusCode)
	_, _ = w.Write(result)
}

func main() {
	if len(os.Args) != 2 {
		log.Fatal("usage: playground web|worker")
	}
	mux := http.NewServeMux()
	health := func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(http.StatusNoContent) }
	mux.HandleFunc("GET /healthz", health)
	mux.HandleFunc("GET /api/v1/health", health)
	var handler http.Handler = mux
	switch os.Args[1] {
	case "worker":
		translator := os.Getenv("JBCC_TRANSLATOR")
		if !filepath.IsAbs(translator) {
			log.Fatal("JBCC_TRANSLATOR must be an absolute path")
		}
		slot := make(chan struct{}, 1)
		mux.HandleFunc("POST /compile", func(w http.ResponseWriter, r *http.Request) {
			select {
			case slot <- struct{}{}:
				defer func() { <-slot }()
				compile(w, r, translator)
			default:
				failure(w, 503, "compiler worker is busy")
			}
		})
	case "web":
		webRoot := os.Getenv("JBCC_WEB_ROOT")
		if webRoot == "" {
			log.Fatal("set JBCC_WEB_ROOT")
		}
		config, err := makeWebServer(context.Background())
		if err != nil {
			log.Fatal(err)
		}
		handler = config.register(mux, webRoot)
	default:
		log.Fatal("usage: playground web|worker")
	}
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	listen := os.Getenv("JBCC_LISTEN_HOST")
	if listen == "" {
		listen = "127.0.0.1"
		if os.Getenv("K_SERVICE") != "" {
			listen = "0.0.0.0"
		}
	}
	addr := net.JoinHostPort(listen, port)
	server := &http.Server{
		Addr: addr, Handler: handler, ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout: 10 * time.Second, WriteTimeout: 25 * time.Second,
		IdleTimeout: 30 * time.Second, MaxHeaderBytes: 16 << 10,
	}
	log.Printf("playground %s listening on %s", os.Args[1], addr)
	log.Fatal(server.ListenAndServe())
}
