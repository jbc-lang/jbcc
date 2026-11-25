package main

import (
	"context"
	"crypto/rand"
	"errors"
	"time"

	"cloud.google.com/go/firestore"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

const rateWindow = time.Minute
const maxBuildsPerWindow = 6
const leaseDuration = 25 * time.Second

var errLimited = errors.New("build limit exceeded")

type buildQuota interface {
	acquire(context.Context, string) (func(), time.Duration, error)
}

type firestoreQuota struct {
	db *firestore.Client
}

type buildHistory struct {
	Recent   []time.Time `firestore:"recent"`
	Lease    string      `firestore:"lease"`
	LeaseEnd time.Time   `firestore:"leaseEnd"`
}

func (b *buildHistory) reserve(now time.Time, lease string) (time.Duration, error) {
	if delay := b.LeaseEnd.Sub(now); b.Lease != "" && delay > 0 {
		return delay, errLimited
	}
	recent := b.Recent[:0]
	for _, started := range b.Recent {
		if started.Add(rateWindow).After(now) {
			recent = append(recent, started)
		}
	}
	if len(recent) >= maxBuildsPerWindow {
		return recent[0].Add(rateWindow).Sub(now), errLimited
	}
	b.Recent = append(recent, now)
	b.Lease, b.LeaseEnd = lease, now.Add(leaseDuration)
	return 0, nil
}

func (q firestoreQuota) acquire(ctx context.Context, uid string) (func(), time.Duration, error) {
	doc := q.db.Collection("compileLimits").Doc(uid)
	lease := rand.Text()
	var delay time.Duration
	err := q.db.RunTransaction(ctx, func(ctx context.Context, tx *firestore.Transaction) error {
		var history buildHistory
		saved, err := tx.Get(doc)
		if err == nil {
			if err = saved.DataTo(&history); err != nil {
				return err
			}
		} else if status.Code(err) != codes.NotFound {
			return err
		}
		delay, err = history.reserve(time.Now(), lease)
		if err != nil {
			return err
		}
		return tx.Set(doc, history)
	})
	if err != nil {
		return nil, delay, err
	}
	return func() {
		// Release a completed or cancelled build. An interrupted process leaves
		// a short lease that expires, so another instance can accept work.
		ctx, cancel := context.WithTimeout(context.WithoutCancel(ctx), 2*time.Second)
		defer cancel()
		_ = q.db.RunTransaction(ctx, func(ctx context.Context, tx *firestore.Transaction) error {
			saved, err := tx.Get(doc)
			if err != nil {
				return err
			}
			var history buildHistory
			if err := saved.DataTo(&history); err != nil {
				return err
			}
			if history.Lease != lease {
				return nil
			}
			return tx.Update(doc, []firestore.Update{{Path: "lease", Value: ""}})
		})
	}, 0, nil
}
