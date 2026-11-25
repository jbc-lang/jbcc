package main

import (
	"context"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"regexp"
	"time"

	"cloud.google.com/go/firestore"
	"google.golang.org/api/iterator"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

var projectID = regexp.MustCompile(`^[A-Za-z0-9_-]{1,64}$`)
var errNoProject = errors.New("saved project not found")
var errConflict = errors.New("saved project changed")

type savedProject struct {
	Project  project `json:"project" firestore:"project"`
	Revision int64   `json:"revision" firestore:"revision"`
}

const projectPageSize = 50

type projectPage struct {
	Names []string `json:"names"`
	Next  string   `json:"next,omitempty"`
}

type projectStore interface {
	list(context.Context, string, string) (projectPage, error)
	get(context.Context, string, string) (savedProject, error)
	save(context.Context, string, string, savedProject) (int64, error)
}

type firestoreProjects struct {
	db *firestore.Client
}

func (s firestoreProjects) collection(uid string) *firestore.CollectionRef {
	return s.db.Collection("users").Doc(uid).Collection("projects")
}

func (s firestoreProjects) doc(uid, id string) *firestore.DocumentRef {
	return s.collection(uid).Doc(id)
}

func (s firestoreProjects) list(ctx context.Context, uid, after string) (projectPage, error) {
	query := s.collection(uid).Select().OrderBy(firestore.DocumentID, firestore.Asc).Limit(projectPageSize + 1)
	if after != "" {
		query = query.StartAfter(after)
	}
	docs := query.Documents(ctx)
	defer docs.Stop()
	page := projectPage{Names: make([]string, 0, projectPageSize)}
	for {
		doc, err := docs.Next()
		if errors.Is(err, iterator.Done) {
			return page, nil
		}
		if err != nil {
			return projectPage{}, err
		}
		if len(page.Names) == projectPageSize {
			page.Next = page.Names[len(page.Names)-1]
			return page, nil
		}
		page.Names = append(page.Names, doc.Ref.ID)
	}
}

func (s firestoreProjects) get(ctx context.Context, uid, id string) (savedProject, error) {
	result, err := s.doc(uid, id).Get(ctx)
	if status.Code(err) == codes.NotFound {
		return savedProject{}, errNoProject
	}
	if err != nil {
		return savedProject{}, err
	}
	var value savedProject
	if err := result.DataTo(&value); err != nil {
		return savedProject{}, err
	}
	if value.Project.Units == nil {
		value.Project.Units = []string{}
	}
	return value, nil
}

func (s firestoreProjects) save(ctx context.Context, uid, id string, value savedProject) (int64, error) {
	ref := s.doc(uid, id)
	err := s.db.RunTransaction(ctx, func(ctx context.Context, tx *firestore.Transaction) error {
		result, err := tx.Get(ref)
		var previous savedProject
		if err == nil {
			if err = result.DataTo(&previous); err != nil {
				return err
			}
		} else if status.Code(err) != codes.NotFound {
			return err
		}
		if value.Revision != previous.Revision {
			return errConflict
		}
		next := value
		next.Revision++
		return tx.Set(ref, next)
	})
	return value.Revision + 1, err
}

func (s *webServer) serveProjects(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Cache-Control", "no-store")
	if !s.sameOrigin(r) {
		failure(w, http.StatusForbidden, "expected a same-origin request")
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()
	uid, ok := s.access.authenticate(w, r.WithContext(ctx))
	if !ok {
		return
	}
	w.Header().Set("Content-Type", "application/json")
	if r.PathValue("id") == "" {
		s.listProjects(w, r, ctx, uid)
		return
	}
	s.serveProject(w, r, ctx, uid)
}

func (s *webServer) listProjects(w http.ResponseWriter, r *http.Request, ctx context.Context, uid string) {
	after := r.URL.Query().Get("after")
	if after != "" && !projectID.MatchString(after) {
		failure(w, http.StatusBadRequest, "invalid project list cursor")
		return
	}
	page, err := s.projects.list(ctx, uid, after)
	if err != nil {
		log.Printf("could not list saved projects: %v", err)
		failure(w, http.StatusServiceUnavailable, "cloud saves temporarily unavailable")
		return
	}
	_ = json.NewEncoder(w).Encode(page)
}

func (s *webServer) serveProject(w http.ResponseWriter, r *http.Request, ctx context.Context, uid string) {
	id := r.PathValue("id")
	if !projectID.MatchString(id) {
		failure(w, http.StatusBadRequest, "invalid saved project name")
		return
	}
	if r.Method == http.MethodGet {
		value, err := s.projects.get(ctx, uid, id)
		if errors.Is(err, errNoProject) {
			failure(w, http.StatusNotFound, "cloud project not found")
		} else if err != nil {
			log.Printf("could not load a saved project: %v", err)
			failure(w, http.StatusServiceUnavailable, "cloud saves temporarily unavailable")
		} else {
			_ = json.NewEncoder(w).Encode(value)
		}
		return
	}

	body, ok := projectBody(w, r)
	if !ok {
		return
	}
	var value savedProject
	const maxRevision = 1<<53 - 1 // JavaScript's maximum safe integer.
	if !strictJSON(body, &value) || value.Revision < 0 || value.Revision >= maxRevision {
		failure(w, http.StatusBadRequest, "invalid project or revision")
		return
	}
	if code, message := value.Project.validate(); code != 0 {
		failure(w, code, message)
		return
	}
	revision, err := s.projects.save(ctx, uid, id, value)
	if errors.Is(err, errConflict) {
		failure(w, http.StatusConflict, "the cloud project changed. Load it before saving")
	} else if err != nil {
		log.Printf("could not save a project: %v", err)
		failure(w, http.StatusServiceUnavailable, "cloud saves temporarily unavailable")
	} else {
		_ = json.NewEncoder(w).Encode(map[string]int64{"revision": revision})
	}
}
