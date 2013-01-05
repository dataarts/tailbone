package tailbone

import (
	"appengine"
	"encoding/json"
	"log"
	"net/http"
)

type HttpHandler func(w http.ResponseWriter, r *http.Request)
type RequestHandler func(c appengine.Context, r *http.Request) (ResponseWritable, error)

type Dict map[string]interface{}
type DictList []Dict
type List []interface{}

type ResponseWritable interface {
	Write(c appengine.Context, w http.ResponseWriter)
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
	c.Infof("WRITING")
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
			resp = Dict{"type": "AppError", "message": err.Error()}
		}
		resp.Write(c, w)
	}
}
