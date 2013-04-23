// Copyright 2013 Google Inc. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package tailbone

import (
	"appengine"
	"appengine/urlfetch"
	"net/http"
	"net/http/httputil"
	"net/url"
	"regexp"
)

var parseProxyUrl = regexp.MustCompile("(/api/(secure)?proxy/)(.*)")

func director(r *http.Request) {
	s := parseProxyUrl.FindStringSubmatch(r.URL.Path)
	if len(s) != 4 {
		return
	}
	var prefix string
	if s[2] == "secure" {
		prefix = "https://"
	} else {
		prefix = "http://"
	}
	resource, err := url.Parse(prefix + s[3])
	if err != nil {
		return
	}
	r.URL = resource
}

func Proxy(w http.ResponseWriter, r *http.Request) {

	// Create Reverse Proxy
	c := appengine.NewContext(r)
	transport := &urlfetch.Transport{Context: c}
	revProxy := &httputil.ReverseProxy{Director: director, Transport: transport}

	// Set public caching
	// w.Header().Set("Cache-Control", "public, max-age=300")
	// w.Header().Set("Pragma", "Public")

	// Cors
	// w.Header().Set("Access-Control-Allow-Origin", "*")

	// Reverse Proxy
	r.Header.Del("Content-Length")
	revProxy.ServeHTTP(w, r)
}

func init() {
	http.HandleFunc("/api/proxy/", Proxy)
	http.HandleFunc("/api/secureproxy/", Proxy)
}
