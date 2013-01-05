package tailbone

import (
	"appengine"
	"errors"
	"net/http"
)

func Events(c appengine.Context, r *http.Request) (ResponseWritable, error) {
	switch r.Method {
	case "POST":
		return Dict{"POST": "thing"}, nil
	}
	return nil, errors.New("Undefined method.")
}

func init() {
	http.HandleFunc("/api/events/", Json(Events))
}
