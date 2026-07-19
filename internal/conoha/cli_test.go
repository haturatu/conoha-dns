package conoha

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
)

func TestShortIDMatchesXXHash64(t *testing.T) {
	if got, want := shortID("hello"), "26c7827d"; got != want {
		t.Fatalf("shortID() = %q, want %q", got, want)
	}
}

func TestActionAliasesAndListOptionalDomain(t *testing.T) {
	cases := []struct {
		args   []string
		action string
	}{
		{[]string{"--auth"}, "auth"}, {[]string{"--renew"}, "renew"},
		{[]string{"-l"}, "list"}, {[]string{"--list", "example.com"}, "list"},
		{[]string{"-ad", "example.com", "host@example.com"}, "add-domain"}, {[]string{"--add-domain", "example.com", "host@example.com"}, "add-domain"},
		{[]string{"-dd", "example.com"}, "delete-domain"}, {[]string{"--delete-domain", "example.com"}, "delete-domain"},
		{[]string{"-ar", "example.com", "@", "A", "192.0.2.1"}, "add-record"}, {[]string{"--add-record", "example.com", "@", "A", "192.0.2.1"}, "add-record"},
		{[]string{"-ur", "example.com", "12345678", "--new-data", "192.0.2.2"}, "update-record"}, {[]string{"--update-record", "example.com", "12345678", "--new-data", "192.0.2.2"}, "update-record"},
		{[]string{"-dr", "example.com", "12345678"}, "delete-record"}, {[]string{"--delete-record", "example.com", "12345678"}, "delete-record"},
	}
	for _, tc := range cases {
		o, err := parse(tc.args, &bytes.Buffer{}, &bytes.Buffer{})
		if err != nil {
			t.Errorf("parse(%q): %v", tc.args, err)
			continue
		}
		if o.action != tc.action {
			t.Errorf("parse(%q).action = %q, want %q", tc.args, o.action, tc.action)
		}
	}
}

func TestMXAndSRVRequirements(t *testing.T) {
	for _, args := range [][]string{{"-ar", "example.com", "mail", "MX", "mail.example.net."}, {"-ar", "example.com", "_sip._tcp", "SRV", "sip.example.net.", "--priority", "1"}} {
		if _, err := parse(args, &bytes.Buffer{}, &bytes.Buffer{}); err == nil {
			t.Errorf("parse(%q) unexpectedly succeeded", args)
		}
	}
}

func TestListCSVUsesStdoutOnly(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v1/domains" {
			t.Errorf("path = %s", r.URL.Path)
			http.NotFound(w, r)
			return
		}
		if r.Header.Get("X-Auth-Token") != "token" {
			t.Errorf("missing token")
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"domains":[{"uuid":"hello","name":"example.com."}]}`))
	}))
	defer server.Close()
	t.Setenv("CONOHA_TOKEN", "token")
	t.Setenv("CONOHA_DNS_API_URL", server.URL)
	t.Setenv("HOME", t.TempDir())
	var stdout, stderr bytes.Buffer
	if err := Run([]string{"-l", "--output", "csv"}, &stdout, &stderr); err != nil {
		t.Fatal(err)
	}
	if got, want := stdout.String(), "ID,Name\n26c7827d,example.com.\n"; got != want {
		t.Fatalf("stdout = %q, want %q", got, want)
	}
	if !strings.Contains(stderr.String(), "CSV") {
		t.Fatalf("stderr = %q, want CSV notice", stderr.String())
	}
	_ = os.Unsetenv("CONOHA_TOKEN")
}

func TestUpdateRecordPreservesOptionalFieldNames(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		switch r.URL.Path {
		case "/v1/domains":
			_, _ = w.Write([]byte(`{"domains":[{"uuid":"domain-uuid","name":"example.com."}]}`))
		case "/v1/domains/domain-uuid/records":
			_, _ = w.Write([]byte(`{"records":[{"uuid":"record-uuid","name":"www.example.com.","type":"SRV","data":"old.","ttl":300,"priority":10,"weight":20,"port":5060}]}`))
		case "/v1/domains/domain-uuid/records/record-uuid":
			if r.Method == http.MethodGet {
				_, _ = w.Write([]byte(`{"uuid":"record-uuid","name":"www.example.com.","type":"SRV","data":"old.","ttl":300,"priority":10,"weight":20,"port":5060}`))
				return
			}
			if got := r.Header.Get("Content-Type"); got != "application/json" {
				t.Errorf("Content-Type = %q, want application/json", got)
			}
			var payload map[string]any
			_ = json.NewDecoder(r.Body).Decode(&payload)
			for key, want := range map[string]float64{"ttl": 301, "priority": 11, "weight": 21, "port": 5061} {
				if got := payload[key]; got != want {
					t.Errorf("payload[%q] = %#v, want %v", key, got, want)
				}
			}
			_, _ = w.Write([]byte(`{"uuid":"record-uuid","name":"www.example.com.","type":"SRV","data":"new.","ttl":301}`))
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()
	t.Setenv("CONOHA_TOKEN", "token")
	t.Setenv("CONOHA_DNS_API_URL", server.URL)
	t.Setenv("HOME", t.TempDir())
	id := shortID("record-uuid")
	var stdout, stderr bytes.Buffer
	err := Run([]string{"-ur", "example.com", id, "--new-data", "new.", "--new-ttl", "301", "--new-priority", "11", "--new-weight", "21", "--new-port", "5061"}, &stdout, &stderr)
	if err != nil {
		t.Fatal(err)
	}
}
