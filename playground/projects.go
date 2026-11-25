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

type projectStore interface {
	get(context.Context, string, string) (savedProject, error)
	save(context.Context, string, string, savedProject) (int64, error)
}

type firestoreProjects struct {
	db *firestore.Client
}

func (s firestoreProjects) doc(uid, id string) *firestore.DocumentRef {
	return s.db.Collection("users").Doc(uid).Collection("projects").Doc(id)
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

func (s *webServer) serveProject(w http.ResponseWriter, r *http.Request) {
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
	id := r.PathValue("id")
	if !projectID.MatchString(id) {
		failure(w, http.StatusBadRequest, "invalid saved project name")
		return
	}
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("Content-Type", "application/json")
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
