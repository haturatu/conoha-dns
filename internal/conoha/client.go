package conoha

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

type Client struct {
	baseURL string
	token   string
	http    *http.Client
	out     io.Writer
	errOut  io.Writer
}

type apiError struct {
	err error
}

func (e apiError) Error() string { return e.err.Error() }

func newClient(renew bool, out, errOut io.Writer) (*Client, error) {
	if err := loadDotEnv(); err != nil {
		return nil, err
	}
	c := &Client{baseURL: envOr("CONOHA_DNS_API_URL", "https://dns-service.c3j1.conoha.io"), http: http.DefaultClient, out: out, errOut: errOut}
	if !renew {
		c.token = os.Getenv("CONOHA_TOKEN")
		if c.token == "" {
			c.token = os.Getenv("API_TOKEN")
		}
	}
	if c.token == "" {
		if err := c.authenticate(); err != nil {
			return nil, err
		}
	}
	return c, nil
}

func (c *Client) authenticate() error {
	user, password, tenant := os.Getenv("CONOHA_USER_ID"), os.Getenv("CONOHA_PASSWORD"), os.Getenv("TENANT_ID")
	if user == "" || password == "" || tenant == "" {
		return fmt.Errorf("APIトークンが見つからず、認証情報 (~/.conoha-envの CONOHA_USER_ID, CONOHA_PASSWORD, TENANT_ID) も不完全です。")
	}
	payload := map[string]any{"auth": map[string]any{"identity": map[string]any{"methods": []string{"password"}, "password": map[string]any{"user": map[string]string{"id": user, "password": password}}}, "scope": map[string]any{"project": map[string]string{"id": tenant}}}}
	body, _ := json.Marshal(payload)
	url := strings.TrimRight(envOr("CONOHA_AUTH_URL", "https://identity.c3j1.conoha.io"), "/") + "/v3/auth/tokens"
	fmt.Fprintln(c.out, "認証して新しいAPIトークンを取得します...")
	req, err := http.NewRequest(http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("Accept", "application/json")
	req.Header.Set("Content-Type", "application/json")
	resp, err := c.http.Do(req)
	if err != nil {
		return apiError{err}
	}
	defer resp.Body.Close()
	token := resp.Header.Get("X-Subject-Token")
	if resp.StatusCode != http.StatusCreated || token == "" {
		contents, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("APIトークンの取得に失敗しました。ステータスコード: %d\nレスポンス: %s", resp.StatusCode, formatJSON(contents))
	}
	c.token = token
	fmt.Fprintln(c.out, "新しいAPIトークンを取得しました。")
	if err := saveToken(token); err != nil {
		fmt.Fprintf(c.out, "警告: %sファイルへの書き込みに失敗しました。手動でトークンを保存してください。エラー: %v\n", envPath(), err)
	} else {
		fmt.Fprintf(c.out, "%sファイルにCONOHA_TOKENを更新しました。\n", envPath())
	}
	return os.Setenv("CONOHA_TOKEN", token)
}

func (c *Client) request(method, path string, payload any, result any) error {
	var body io.Reader
	if payload != nil {
		raw, err := json.Marshal(payload)
		if err != nil {
			return err
		}
		body = bytes.NewReader(raw)
	}
	req, err := http.NewRequest(method, strings.TrimRight(c.baseURL, "/")+path, body)
	if err != nil {
		return err
	}
	req.Header.Set("Accept", "application/json")
	req.Header.Set("X-Auth-Token", c.token)
	if payload != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := c.http.Do(req)
	if err != nil {
		return apiError{err}
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		raw, _ := io.ReadAll(resp.Body)
		return apiError{fmt.Errorf("ステータスコード: %d\nレスポンス: %s", resp.StatusCode, formatJSON(raw))}
	}
	if result != nil && resp.StatusCode != http.StatusNoContent {
		if err := json.NewDecoder(resp.Body).Decode(result); err != nil {
			return apiError{err}
		}
	}
	return nil
}

func formatJSON(raw []byte) string {
	var value any
	if json.Unmarshal(raw, &value) == nil {
		pretty, _ := json.MarshalIndent(value, "", "  ")
		return string(pretty)
	}
	return string(raw)
}
func envOr(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}
func envPath() string {
	home, err := os.UserHomeDir()
	if err != nil {
		return ".conoha-env"
	}
	return filepath.Join(home, ".conoha-env")
}

func loadDotEnv() error {
	raw, err := os.ReadFile(envPath())
	if errors.Is(err, os.ErrNotExist) {
		return nil
	}
	if err != nil {
		return err
	}
	for _, line := range strings.Split(string(raw), "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		pair := strings.SplitN(line, "=", 2)
		if len(pair) != 2 || os.Getenv(pair[0]) != "" {
			continue
		}
		os.Setenv(pair[0], strings.Trim(strings.TrimSpace(strings.SplitN(pair[1], "#", 2)[0]), "\"'"))
	}
	return nil
}

func saveToken(token string) error {
	path := envPath()
	raw, err := os.ReadFile(path)
	if err != nil && !errors.Is(err, os.ErrNotExist) {
		return err
	}
	lines := []string{}
	if err == nil {
		for _, line := range strings.Split(string(raw), "\n") {
			if !strings.HasPrefix(line, "CONOHA_TOKEN=") && line != "" {
				lines = append(lines, line)
			}
		}
	}
	lines = append(lines, "CONOHA_TOKEN="+token)
	return os.WriteFile(path, []byte(strings.Join(lines, "\n")+"\n"), 0600)
}
