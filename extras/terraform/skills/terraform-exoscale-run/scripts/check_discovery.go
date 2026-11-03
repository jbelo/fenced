package main

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"net/url"
	"os"
	"time"

	exoscale "github.com/exoscale/egoscale/v3"
	"github.com/exoscale/egoscale/v3/credentials"
)

// Run from the selected provider module so this uses its SDK, not another version.
func main() {
	err := checkDiscovery(os.Getenv("EXOSCALE_API_ENDPOINT"), os.Getenv("EXPECTED_API_ENDPOINT"),
		os.Getenv("ZONE"), os.Getenv("EXO_KEY"), os.Getenv("EXO_SECRET"))
	if err != nil {
		fmt.Fprintln(os.Stderr, "FAIL:", err)
		os.Exit(1)
	}
	fmt.Println("PASS: SDK discovery matched the approved API endpoint and its signed KMS read succeeded")
}

func checkDiscovery(bootstrap, expectedAPI, zone, key, secret string) error {
	for _, value := range []string{bootstrap, expectedAPI, zone, key, secret} {
		if value == "" {
			return errors.New("set EXOSCALE_API_ENDPOINT, EXPECTED_API_ENDPOINT, ZONE, EXO_KEY and EXO_SECRET")
		}
	}
	for _, endpoint := range []string{bootstrap, expectedAPI} {
		u, err := url.Parse(endpoint)
		if err != nil || (u.Scheme != "http" && u.Scheme != "https") || u.Host == "" ||
			u.User != nil || u.RawQuery != "" || u.Fragment != "" {
			return errors.New("use approved HTTP(S) endpoints without embedded credentials, query or fragment")
		}
	}

	client, err := exoscale.NewClient(credentials.NewStaticCredentials(key, secret),
		exoscale.ClientOptWithEndpoint(exoscale.Endpoint(bootstrap)),
		exoscale.ClientOptWithHTTPClient(&http.Client{
			CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse },
		}))
	if err != nil {
		return errors.New("SDK client configuration failed")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	endpoint, err := client.GetZoneAPIEndpoint(ctx, exoscale.ZoneName(zone))
	if err != nil {
		return errors.New("SDK zone discovery failed; inspect sanitized server diagnostics")
	}
	if endpoint != exoscale.Endpoint(expectedAPI) {
		return errors.New("unexpected discovered API endpoint; protected request not sent")
	}
	if _, err := client.WithEndpoint(endpoint).ListKmsKeys(ctx); err != nil {
		return errors.New("discovery matched, but signed KMS listing at the approved API failed")
	}
	return nil
}
