package tailbone

import (
	"appengine"
	"appengine/user"
	"log"
	"runtime"
	// "appengine/datastore"
	// "appengine/blobstore"
	"fmt"
	"encoding/json"
	"net/http"
	"errors"
	"strings"
)

type httpHandler func(w http.ResponseWriter, r *http.Request)
type requestHandler func(c appengine.Context, r *http.Request) (interface{}, error)

type dict map[string]interface{}

func parseRestfulPath(str string) (model, id string, err error) {
	s := strings.Split(str, "/")
	l := len(s)
	switch l {
	case 3:
		return s[2], "", nil
	case 4:
		return s[2], s[3], nil
	}
	return "", "", errors.New(fmt.Sprintf("Unparsable url: %s", str))
}

func Restful(c appengine.Context, r *http.Request) (interface{}, error) {
	model, id, err := parseRestfulPath(r.URL.Path)
	if (err != nil) { return nil, err }
	c.Infof("Model: %s, ID: %s", model, id)
	switch r.Method {
	case "GET":
		return dict{"method": "get"}, nil
	case "POST":
		return dict{"method": "post"}, nil
	case "PUT":
		return dict{"method": "put"}, nil
	case "DELETE":
		return dict{"method": "delete"}, nil
	}
	return nil, errors.New("Undefined method.")
}

func Json(h requestHandler) httpHandler {
	return func(w http.ResponseWriter, r *http.Request) {
		c := appengine.NewContext(r)
		resp, err := h(c, r)
		if err != nil {
			// switch err {
			//   case ErrLoginRequired:
			//    resp = m{"error": err}
			// }
			resp = dict{"error": err.Error()}
		}
		if resp != nil {
			w.Header().Set("content-type", "application/json")
			encoder := json.NewEncoder(w)
			encoder.Encode(resp)
		}
	}
}

func Login(w http.ResponseWriter, r *http.Request) {
	c := appengine.NewContext(r)
	url, _ := user.LoginURL(c, "/")
	http.Redirect(w, r, url, http.StatusFound)
}

func Logout(w http.ResponseWriter, r *http.Request) {
	c := appengine.NewContext(r)
	url, _ := user.LogoutURL(c, "/")
	http.Redirect(w, r, url, http.StatusFound)
}

// Here logs the caller file and line number where it was called from.
func here() {
	_, file, line, _ := runtime.Caller(1)
	log.Printf("%s:%d", file, line)
}

func init() {
	http.HandleFunc("/api/", Json(Restful))
}
