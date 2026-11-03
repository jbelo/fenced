package main

import (
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"
)

func TestDiscoveryRouting(t *testing.T) {
	for _, mode := range []string{"success", "unexpected endpoint", "redirect"} {
		t.Run(mode, func(t *testing.T) {
			var foreignCalls, protectedCalls atomic.Int32
			foreign := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				foreignCalls.Add(1)
				w.WriteHeader(http.StatusForbidden)
			}))
			t.Cleanup(foreign.Close)
			var server *httptest.Server
			server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				w.Header().Set("Content-Type", "application/json")
				switch r.URL.Path {
				case "/zone":
					if r.Method != http.MethodGet || r.Header.Get("Authorization") != "" {
						t.Error("initial discovery must be an unsigned GET")
					}
					if mode == "redirect" {
						http.Redirect(w, r, foreign.URL+"/zone", http.StatusFound)
						return
					}
					endpoint := server.URL + "/v2"
					if mode == "unexpected endpoint" {
						endpoint = foreign.URL + "/v2"
					}
					fmt.Fprintf(w, `{"zones":[{"name":"ch-gva-2","api-endpoint":%q}]}`, endpoint)
				case "/v2/kms-key":
					protectedCalls.Add(1)
					if r.Method != http.MethodGet || !strings.HasPrefix(r.Header.Get("Authorization"), "EXO2-HMAC-SHA256 ") {
						t.Error("protected read must be a signed GET")
					}
					fmt.Fprint(w, `{"kms-keys":[]}`)
				default:
					t.Error("unexpected request path")
					w.WriteHeader(http.StatusNotFound)
				}
			}))
			t.Cleanup(server.Close)

			err := checkDiscovery(server.URL, server.URL+"/v2", "ch-gva-2", "EXOlocaltest", "local-test-secret")
			if (err == nil) != (mode == "success") {
				t.Fatalf("unexpected check outcome: %v", err)
			}
			if mode == "unexpected endpoint" && !strings.Contains(err.Error(), "protected request not sent") {
				t.Fatal("endpoint mismatch was not rejected before the protected read")
			}
			wantProtected := int32(0)
			if mode == "success" {
				wantProtected = 1
			}
			if protectedCalls.Load() != wantProtected || foreignCalls.Load() != 0 {
				t.Fatal("request escaped its approved route or protected read was not performed")
			}
		})
	}
}

func TestMissingInputs(t *testing.T) {
	if checkDiscovery("", "", "", "", "") == nil {
		t.Fatal("missing explicit inputs must not use implicit endpoints or credentials")
	}
}
