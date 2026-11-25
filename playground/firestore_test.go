package main

import (
	"context"
	"crypto/rand"
	"errors"
	"os"
	"slices"
	"sync"
	"testing"
	"time"

	"cloud.google.com/go/firestore"
	"golang.org/x/oauth2"
	"google.golang.org/api/option"
)

func TestFirestoreSharedLimitsAndPrivateProjects(t *testing.T) {
	projectID := os.Getenv("JBCC_TEST_FIRESTORE_PROJECT")
	database := os.Getenv("JBCC_TEST_FIRESTORE_DATABASE")
	if projectID == "" || database == "" {
		t.Skip("set JBCC_TEST_FIRESTORE_PROJECT and JBCC_TEST_FIRESTORE_DATABASE")
	}
	var options []option.ClientOption
	if token := os.Getenv("JBCC_TEST_FIRESTORE_TOKEN"); token != "" {
		options = append(options, option.WithTokenSource(oauth2.StaticTokenSource(&oauth2.Token{AccessToken: token})))
	}
	ctx, cancel := context.WithTimeout(context.Background(), 40*time.Second)
	defer cancel()
	open := func() *firestore.Client {
		t.Helper()
		db, err := firestore.NewClientWithDatabase(ctx, projectID, database, options...)
		if err != nil {
			t.Fatal(err)
		}
		t.Cleanup(func() { db.Close() })
		return db
	}
	db1, db2 := open(), open()
	first, second := firestoreQuota{db1}, firestoreQuota{db2}
	uid := "playground-test-" + rand.Text()
	p1, p2 := firestoreProjects{db1}, firestoreProjects{db2}
	t.Cleanup(func() {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		for _, doc := range []*firestore.DocumentRef{db1.Collection("compileLimits").Doc(uid), p1.doc(uid, "draft"), p1.doc(uid, "second")} {
			if _, err := doc.Delete(ctx); err != nil {
				t.Errorf("delete disposable test document: %v", err)
			}
		}
	})

	var wait sync.WaitGroup
	start := make(chan struct{})
	results := make(chan struct {
		release func()
		err     error
	}, 2)
	for _, quota := range []firestoreQuota{first, second} {
		wait.Add(1)
		go func() {
			defer wait.Done()
			<-start
			release, _, err := quota.acquire(ctx, uid)
			results <- struct {
				release func()
				err     error
			}{release, err}
		}()
	}
	close(start)
	wait.Wait()
	close(results)
	var leases, denials int
	for result := range results {
		switch {
		case result.err == nil:
			leases++
			result.release()
		case errors.Is(result.err, errLimited):
			denials++
		default:
			t.Fatal(result.err)
		}
	}
	if leases != 1 || denials != 1 {
		t.Fatalf("expected one lease and one denial, got %d and %d", leases, denials)
	}
	for i := 1; i < maxBuildsPerWindow; i++ {
		release, _, err := second.acquire(ctx, uid)
		if err != nil {
			t.Fatal(err)
		}
		release()
	}
	if _, _, err := first.acquire(ctx, uid); !errors.Is(err, errLimited) {
		t.Fatalf("expected a shared limit, got %v", err)
	}

	source, err := os.ReadFile("../tests/programs/hello.b")
	if err != nil {
		t.Fatal(err)
	}
	draft := savedProject{Project: project{Entry: "hello.b", Files: []sourceFile{{Path: "hello.b", Source: string(source)}}}}
	if revision, err := p1.save(ctx, uid, "draft", draft); err != nil || revision != 1 {
		t.Fatalf("create draft: revision %d, %v", revision, err)
	}
	if _, err := p2.save(ctx, uid, "draft", draft); !errors.Is(err, errConflict) {
		t.Fatalf("stale writer received %v", err)
	}
	if loaded, err := p2.get(ctx, uid, "draft"); err != nil || loaded.Revision != 1 || loaded.Project.Files[0].Source != string(source) || loaded.Project.Units == nil {
		t.Fatalf("load draft: revision %d, %v", loaded.Revision, err)
	}
	draft.Revision = 1
	if revision, err := p2.save(ctx, uid, "draft", draft); err != nil || revision != 2 {
		t.Fatalf("update draft: revision %d, %v", revision, err)
	}
	if _, err := p2.get(ctx, uid+"-other", "draft"); !errors.Is(err, errNoProject) {
		t.Fatalf("another user's project returned %v", err)
	}
	draft.Revision = 0
	if _, err := p1.save(ctx, uid, "second", draft); err != nil {
		t.Fatal(err)
	}
	page, err := p2.list(ctx, uid, "")
	if err != nil || !slices.Equal(page.Names, []string{"draft", "second"}) || page.Next != "" {
		t.Fatalf("list projects: %+v, %v", page, err)
	}
	page, err = p2.list(ctx, uid, "draft")
	if err != nil || !slices.Equal(page.Names, []string{"second"}) {
		t.Fatalf("list after draft: %+v, %v", page, err)
	}
	page, err = p2.list(ctx, uid+"-other", "")
	if err != nil || page.Names == nil || len(page.Names) != 0 {
		t.Fatalf("list another user's projects: %+v, %v", page, err)
	}
}
