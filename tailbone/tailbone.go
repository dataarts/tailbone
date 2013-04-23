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
	"appengine/user"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"regexp"
)

type HttpHandler func(w http.ResponseWriter, r *http.Request)
type RequestHandler func(c appengine.Context, r *http.Request) (ResponseWritable, error)

type Dict map[string]interface{}
type DictList []Dict
type List []interface{}

type ResponseWritable interface {
	Write(c appengine.Context, w http.ResponseWriter)
}

type AppError struct {
	What string
}

func (e AppError) Error() string {
	return e.What
}

type LoginError struct {
	AppError
}

func (e LoginError) Error() string {
	return "Login Required."
}

func (d Dict) scoped() {
	if owners, ok := d["owners"]; ok {
		log.Println(owners)
		if o, ok := owners.([]string); ok {
			for x := range o {
				log.Println(x)
			}
		}
	}
}

func (resp Dict) Write(c appengine.Context, w http.ResponseWriter) {
	w.Header().Set("content-type", "application/json")
	encoder := json.NewEncoder(w)
	resp.scoped()
	encoder.Encode(resp)
}

func (resp DictList) Write(c appengine.Context, w http.ResponseWriter) {
	w.Header().Set("content-type", "application/json")
	for _, d := range resp {
		d.scoped()
	}
	encoder := json.NewEncoder(w)
	encoder.Encode(resp)
}

func Json(h RequestHandler) HttpHandler {
	return func(w http.ResponseWriter, r *http.Request) {
		c := appengine.NewContext(r)
		resp, err := h(c, r)
		if err != nil {
			switch err.(type) {
			case LoginError:
				resp = Dict{
					"type":    "LoginError",
					"message": err.Error(),
				}
			case AppError:
				resp = Dict{
					"type":    "AppError",
					"message": err.Error(),
				}
			}
		}
		resp.Write(c, w)
	}
}

func Login(w http.ResponseWriter, r *http.Request) {
	c := appengine.NewContext(r)
	redirect := r.URL.Query().Get("redirect")
	url, _ := user.LoginURL(c, redirect)
	http.Redirect(w, r, url, http.StatusFound)
}

func Logout(w http.ResponseWriter, r *http.Request) {
	c := appengine.NewContext(r)
	redirect := r.URL.Query().Get("redirect")
	url, _ := user.LogoutURL(c, redirect)
	http.Redirect(w, r, url, http.StatusFound)
}

var parseTestUrl = regexp.MustCompile("/api/test/(.*)")

func serveJsTests(w http.ResponseWriter, r *http.Request) {
	s := parseTestUrl.FindStringSubmatch(r.URL.Path)
	if len(s) != 2 {
		return
	}
	http.ServeFile(w, r, fmt.Sprintf("tailbone/test/%s.html", s[1]))
}

func init() {
	http.HandleFunc("/api/login", Login)
	http.HandleFunc("/api/logout", Logout)
	if appengine.IsDevAppServer() {
		http.HandleFunc("/api/test/", serveJsTests)
	}
}
