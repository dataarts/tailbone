package tailbone

import (
	"appengine"
	"appengine/user"
	"appengine/datastore"
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

func parseRestfulPath(str string) (kind, id string, err error) {
	s := strings.Split(str, "/")
	l := len(s)
	kind = strings.ToLower(s[2])
	switch l {
	case 3:
		id = ""
	case 4:
		id = s[3]
	default:
		err = errors.New(fmt.Sprintf("Unparsable url: %s", str))
	}
	return
}

func parseBody(r *http.Request) (interface{}, error) {
	contentType := strings.Split(r.Header.Get("Content-Type"),";")[0]
	switch	contentType {
	case "application/json":
		var data dict
		decoder := json.NewDecoder(r.Body)
		err := decoder.Decode(&data)
		if err != nil {
			return nil, err
		}
		return data, nil
	case "application/x-www-form-urlencoded":
		return nil, errors.New("Unsupported Content-Type")
	}
	return nil, errors.New("Unsupported Content-Type")
}

func Restful(c appengine.Context, r *http.Request) (interface{}, error) {
	kind, id, err := parseRestfulPath(r.URL.Path)
	if (err != nil) { return nil, err }
	switch r.Method {
	case "GET":
		if id == "" {
			items := []dict{}
			q := datastore.NewQuery(kind)
			for t := q.Run(c); ; {
				var x dict
				key, err := t.Next(&x)
				c.Infof("Key %s", key)
				if err == datastore.Done {
					break
				}
				if err != nil {
					return nil, err
				}
				items = append(items, x)
			}
			return items, nil
		} else {
			return dict{"method": "get"}, nil
		}
	case "POST":
		data, err := parseBody(r)
		key := datastore.NewIncompleteKey(c, kind, nil)
		datastore.Put(c, key, data)
		if err != nil {
			return nil, err
		}
		return data, nil
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
			//	 case ErrLoginRequired:
			//		resp = m{"error": err}
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

func init() {
	http.HandleFunc("/api/", Json(Restful))
}
