package main

import (
	"context"
	"errors"
	"net/http"
	"regexp"
	"strconv"
	"strings"

	"firebase.google.com/go/v4/auth"
)

var firebaseUID = regexp.MustCompile(`^[A-Za-z0-9_-]{1,128}$`)

type tokenVerifier interface {
	VerifyIDToken(context.Context, string) (*auth.Token, error)
}

type accessPolicy struct {
	verifier tokenVerifier
	allowed  map[string]bool
}

func githubAllowlist(value string) (map[string]bool, error) {
	allowed := make(map[string]bool)
	for item := range strings.SplitSeq(value, ",") {
		item = strings.TrimSpace(item)
		number, err := strconv.ParseUint(item, 10, 64)
		if err != nil || number == 0 || strconv.FormatUint(number, 10) != item {
			return nil, errors.New("JBCC_ALLOWED_GITHUB_IDS must contain comma-separated numeric GitHub account IDs")
		}
		allowed[item] = true
	}
	return allowed, nil
}

func (a accessPolicy) authenticate(w http.ResponseWriter, r *http.Request) (string, bool) {
	scheme, token, found := strings.Cut(r.Header.Get("Authorization"), " ")
	if !found || !strings.EqualFold(scheme, "Bearer") || token == "" {
		failure(w, http.StatusUnauthorized, "sign in with GitHub")
		return "", false
	}
	id, err := a.verifier.VerifyIDToken(r.Context(), token)
	if err != nil {
		failure(w, http.StatusUnauthorized, "GitHub session is invalid or expired")
		return "", false
	}
	identities, _ := id.Firebase.Identities["github.com"].([]any)
	if !firebaseUID.MatchString(id.UID) || id.Firebase.SignInProvider != "github.com" || len(identities) != 1 {
		failure(w, http.StatusForbidden, "a verified GitHub identity is required")
		return "", false
	}
	github, _ := identities[0].(string)
	if !a.allowed[github] {
		failure(w, http.StatusForbidden, "this GitHub account does not have playground access")
		return "", false
	}
	return id.UID, true
}
