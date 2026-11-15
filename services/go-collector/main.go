package main

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"os"

	"dc-collector/collector"
)

func main() {
	counts := collector.Poll(context.Background(), os.Args[1:], 2, func(ctx context.Context, url string) error {
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
		if err != nil {
			return err
		}
		response, err := http.DefaultClient.Do(req)
		if err != nil {
			return err
		}
		defer response.Body.Close()
		_, _ = io.Copy(io.Discard, response.Body)
		if response.StatusCode != http.StatusOK {
			return fmt.Errorf("status %d", response.StatusCode)
		}
		return nil
	})
	fmt.Printf("ok=%d errors=%d\n", counts.OK, counts.Errors)
}
