package tailbone

import (
	"appengine"
	"appengine/user"
	"appengine/datastore"
	// "appengine/blobstore"
	"fmt"
	"log"
	"encoding/json"
	"net/http"
	"errors"
	"strings"
	"strconv"
	"regexp"
)

type HttpHandler func(w http.ResponseWriter, r *http.Request)
type RequestHandler func(c appengine.Context, r *http.Request) (interface{}, error)

type Dict map[string]interface{}

func (d Dict) Load(c <-chan datastore.Property) error {
	log.Printf("Loading")
	for p := range c {
    log.Printf("Property: %s, Name: %s, Value: %s", p, p.Name, p.Value)
		d[p.Name] = p.Value
	}
	return nil
}

func (d Dict) SaveWithPrefix(prefix string, c chan<- datastore.Property) error {
  return nil
}

func (d Dict) Save(c chan<- datastore.Property) error {
	log.Printf("Saving")
	defer close(c)
	for k, v := range d {
		switch t := v.(type) {
		case map[string]interface{}:
			log.Printf("type: map")
			// v.SaveWithPrefix(k,c)
		case []interface{}:
			log.Printf("type: slice")
		case float64, float32:
			log.Printf("type: float64")
		case int, int32, int64:
			log.Printf("type: int")
      v = v.(float64)
		case string:
			log.Printf("type: string")
		case bool:
			log.Printf("type: bool")
		default:
			log.Printf("type: %s", t)
		}
		log.Printf("Key: %s Value: %s", k, v)
		c <- datastore.Property {
			Name: k,
			Value: v,
		}
	}
	return nil
}

func ParseRestfulPath(str string) (kind, id string, err error) {
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

var (
  re_filter = regexp.MustCompile("^([\\w\\-.]+)(!=|==|=|<=|>=|<|>)(.+)$")
  re_composite_filter = regexp.MustCompile("^(AND|OR)\\((.*)\\)$")
  re_split = regexp.MustCompile(",\\W*")
)

func appendFilter(q *datastore.Query, name, op, value string) (*datastore.Query, error) {
  if op == "==" {
    op = "="
  }
  log.Printf("query filter added %s %s %s", name, op, value)
  floatValue, err := strconv.ParseFloat(value, 64)
  if err != nil {
    return q.Filter(name + " " + op, value), nil
  }
  return q.Filter(name + " " + op, floatValue), nil
}

func parseFilter(q *datastore.Query, filter string) (*datastore.Query, error) {
  // Go api does not yet support composite filters such as OR or AND so this is left undone
  composite := re_composite_filter.FindStringSubmatch(filter)
  if len(composite) == 0 {
    f := re_filter.FindStringSubmatch(filter)
    if len(f) != 4 {
      return nil, errors.New("Incorrectly formated filter.")
    }
    var err error
    q, err = appendFilter(q, f[1], f[2], f[3])
    if err != nil {
      return nil, err
    }
  } else {
    return nil, errors.New("Composite filters like OR/AND are not supported in Go version.")
  }
  return q, nil
}

func PopulateQuery(q *datastore.Query, r *http.Request) (*datastore.Query, error) {
  query := r.URL.Query()
  if params, ok := query["params"]; ok {
    log.Printf(params[0])
  } else {
    if filters, ok := query["filter"]; ok {
      var err error
      for _, filter := range filters {
        q, err = parseFilter(q, filter)
        if err != nil {
          return nil, err
        }
      }
    }
    if orders, ok := query["order"]; ok {
      for _, order := range orders {
        q = q.Order(order)
      }
    }
  }
  return q, nil
}

func ParseBody(r *http.Request) (interface{}, error) {
	contentType := strings.Split(r.Header.Get("Content-Type"),";")[0]
	switch contentType {
	case "application/json":
		var data Dict
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
	kind, id, err := ParseRestfulPath(r.URL.Path)
	if (err != nil) { return nil, err }
	switch r.Method {
	case "GET":
		if id == "" {
			items := []Dict{}
			q := datastore.NewQuery(kind)
      q, err := PopulateQuery(q, r)
      if err != nil {
        return nil, err
      }
			for t := q.Run(c); ; {
        x := make(Dict)
				key, err := t.Next(&x)
				c.Infof("Key: %s", key)
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
			return Dict{"method": "get"}, nil
		}
	case "POST":
		data, err := ParseBody(r)
		log.Printf("POST data: %s", data)
		key := datastore.NewIncompleteKey(c, kind, nil)
		datastore.Put(c, key, data)
		if err != nil {
			return nil, err
		}
		return data, nil
	case "PUT":
		return Dict{"method": "put"}, nil
	case "DELETE":
		return Dict{"method": "delete"}, nil
	}
	return nil, errors.New("Undefined method.")
}

func Json(h RequestHandler) HttpHandler {
	return func(w http.ResponseWriter, r *http.Request) {
		c := appengine.NewContext(r)
		resp, err := h(c, r)
		if err != nil {
			// switch err {
			//	 case ErrLoginRequired:
			//		resp = m{"error": err}
			// }
      resp = Dict{"type": "error", "message": err.Error()}
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
