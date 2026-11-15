package collector

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestTrySendDropsWhenTheBufferIsFull(t *testing.T) {
	ch := make(chan string, 1)
	if !TrySend(ch, "first") {
		t.Fatal("first send should fit")
	}
	if TrySend(ch, "second") {
		t.Fatal("second send should drop")
	}
}

func TestPollReadsEveryServer(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()
	urls := []string{server.URL, server.URL, server.URL, server.URL}
	counts := Poll(context.Background(), urls, 2, func(ctx context.Context, url string) error {
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
		if err != nil {
			return err
		}
		response, err := http.DefaultClient.Do(req)
		if err != nil {
			return err
		}
		defer response.Body.Close()
		if response.StatusCode != http.StatusOK {
			return http.ErrNotSupported
		}
		return nil
	})
	if counts.OK != 4 || counts.Errors != 0 {
		t.Fatalf("counts %+v", counts)
	}
}
