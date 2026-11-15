package collector

import "context"

func TrySend(ch chan string, item string) bool {
	select {
	case ch <- item:
		return true
	default:
		return false
	}
}

type Counts struct {
	OK     int
	Errors int
}

func Poll(ctx context.Context, urls []string, workers int, fetch func(context.Context, string) error) Counts {
	if workers < 1 {
		workers = 1
	}
	jobs := make(chan string)
	results := make(chan error, len(urls))
	for range workers {
		go func() {
			for url := range jobs {
				results <- fetch(ctx, url)
			}
		}()
	}
	for _, url := range urls {
		jobs <- url
	}
	close(jobs)
	var counts Counts
	for range urls {
		if err := <-results; err != nil {
			counts.Errors++
			continue
		}
		counts.OK++
	}
	return counts
}
