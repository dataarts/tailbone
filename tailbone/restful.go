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
	"appengine/datastore"
	"appengine/user"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"regexp"
	"strconv"
	"strings"
)

func (d Dict) Load(c <-chan datastore.Property) error {
	for p := range c {
		key := p.Name
		dict := d
		if strings.Contains(p.Name, ".") {
			names := strings.Split(p.Name, ".")
			for _, n := range names[:len(names)-1] {
				value, exists := dict[n]
				if exists {
					switch value.(type) {
					case []interface{}:
						dict_ := make(Dict)
						dict[n] = append(value.([]interface{}), dict_)
						dict = dict_
					default:
						dict = value.(Dict)
					}
				} else {
					dict[n] = make(Dict)
					dict = dict[n].(Dict)
				}
			}
			key = names[len(names)-1]
		}
		value, exists := dict[key]
		if exists {
			switch value.(type) {
			case []interface{}:
				value = append(value.([]interface{}), p.Value)
			default:
				value = []interface{}{value, p.Value}
			}
		} else if p.Multiple {
			value = []interface{}{p.Value}
		} else {
			value = p.Value
		}
		dict[key] = value
	}
	return nil
}

func saveWithPrefix(d map[string]interface{},
	prefix string,
	c chan<- datastore.Property,
	multiple bool) error {
	for k, v := range d {
		save(prefix+"."+k, v, c, multiple)
	}
	return nil
}

// []byte fields more than 1 megabyte long will not be loaded or saved.
const maxBlobLen = 1 << 20

func save(k string, v interface{}, c chan<- datastore.Property, multiple bool) error {
	noIndex := false
	switch t := v.(type) {
	case map[string]interface{}:
		saveWithPrefix(v.(map[string]interface{}), k, c, multiple)
		return nil
	case []interface{}:
		for _, x := range v.([]interface{}) {
			err := save(k, x, c, true)
			if err != nil {
				return err
			}
		}
		return nil
	case float64, float32, int, int32, int64:
		v = v.(float64)
	case string:
		b := []byte(v.(string))
		if len(b) >= maxBlobLen {
			noIndex = true
		}
	case bool:
		// pass
	default: // time.Time, *datastore.Key, []byte
		log.Printf("UNKNOWN type: %s", t)
	}
	c <- datastore.Property{
		Name:     k,
		Value:    v,
		NoIndex:  noIndex,
		Multiple: multiple,
	}
	return nil
}

func (d Dict) Save(c chan<- datastore.Property) error {
	defer close(c)
	for k, v := range d {
		err := save(k, v, c, false)
		if err != nil {
			return err
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
		err = AppError{fmt.Sprintf("Unparsable url: %s", str)}
	}
	return
}

var (
	re_filter           = regexp.MustCompile("^([\\w\\-.]+)(!=|==|=|<=|>=|<|>)(.+)$")
	re_composite_filter = regexp.MustCompile("^(AND|OR)\\((.*)\\)$")
	re_split            = regexp.MustCompile(",\\W*")
	re_image            = regexp.MustCompile("image/(png|jpeg|jpg|webp|gif|bmp|tiff|ico)")
)

func appendFilter(q *datastore.Query, name, op, value string) (*datastore.Query, error) {
	if op == "==" {
		op = "="
	}
	log.Printf("query filter added %s %s %s", name, op, value)
	floatValue, err := strconv.ParseFloat(value, 64)
	if err != nil {
		return q.Filter(name+" "+op, value), nil
	}
	return q.Filter(name+" "+op, floatValue), nil
}

func parseFilter(q *datastore.Query, filter string) (*datastore.Query, error) {
	// Go api does not yet support composite filters such as OR or AND so this is left undone
	composite := re_composite_filter.FindStringSubmatch(filter)
	if len(composite) == 0 {
		f := re_filter.FindStringSubmatch(filter)
		if len(f) != 4 {
			return nil, AppError{"Incorrectly formated filter."}
		}
		var err error
		q, err = appendFilter(q, f[1], f[2], f[3])
		if err != nil {
			return nil, err
		}
	} else {
		return nil, AppError{"Composite filters like OR/AND are not supported in Go version."}
	}
	return q, nil
}

func PopulateQuery(q *datastore.Query, r *http.Request) (*datastore.Query, error) {
	query := r.URL.Query()
	if params, ok := query["params"]; ok {
		_ = params
		log.Printf("%s", params)
		return nil, AppError{"Query by params, not yet supported."}
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

func ParseBody(r *http.Request) (Dict, error) {
	contentType := strings.Split(r.Header.Get("Content-Type"), ";")[0]
	switch contentType {
	case "application/json":
		var data Dict
		defer r.Body.Close()
		decoder := json.NewDecoder(r.Body)
		err := decoder.Decode(&data)
		if err != nil {
			return nil, err
		}
		return data, nil
	case "application/x-www-form-urlencoded":
		return nil, AppError{"Unsupported Content-Type."}
	}
	return nil, AppError{"Unsupported Content-Type."}
}

func newKey(c appengine.Context, kind, id string, parent *datastore.Key) *datastore.Key {
	i, err := strconv.ParseInt(id, 10, 64)
	if err != nil {
		return datastore.NewKey(c, kind, id, 0, nil)
	}
	return datastore.NewKey(c, kind, "", i, nil)
}

func getID(key *datastore.Key) interface{} {
	intID := key.IntID()
	if intID != 0 {
		return intID
	}
	return key.StringID()
}

func query(c appengine.Context, r *http.Request, kind string) (ResponseWritable, error) {
	items := DictList{}
	q := datastore.NewQuery(kind)
	q, err := PopulateQuery(q, r)
	if err != nil {
		return nil, err
	}
	for t := q.Run(c); ; {
		x := Dict{}
		key, err := t.Next(x)
		if err == datastore.Done {
			break
		}
		if err != nil {
			return nil, err
		}
		x["Id"] = getID(key)
		items = append(items, x)
	}
	return items, nil
}

var (
	asciiLetters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
)

func convertNumToStr(num string) (string, error) {
	var (
		x, y int64
		l    = len(num)
		str  string
		err  error
	)
	for i := 0; i < l; {
		if i == l-1 {
			str += string(asciiLetters[i])
			break
		}
		x, err = strconv.ParseInt(string(num[i]), 10, 64)
		if err != nil {
			break
		}
		y, err = strconv.ParseInt(string(num[i+1]), 10, 64)
		if err != nil {
			break
		}
		n := x + y
		if n < 52 {
			str += string(asciiLetters[n])
			i += 2
		} else {
			str += string(asciiLetters[x])
			i += 1
		}
	}
	return str, err
}

func convertStrToNum(str string) (num string) {
	for _, x := range str {
		num += strconv.FormatInt(int64(strings.Index(asciiLetters, string(x))), 10)
	}
	return
}

func isOwner(c appengine.Context, u *user.User, key *datastore.Key) error {
	item := Dict{}
	err := datastore.Get(c, key, item)
	if err != nil {
		return err
	}
	return nil
}

func Restful(c appengine.Context, r *http.Request) (ResponseWritable, error) {
	kind, id, err := ParseRestfulPath(r.URL.Path)
	if err != nil {
		return nil, err
	}
	switch r.Method {
	case "GET":
		if id == "" {
			items, err := query(c, r, kind)
			if err != nil {
				return nil, err
			}
			return items, nil
		} else {
			if kind == "users" && id == "me" {
				u := user.Current(c)
				if u == nil {
					return nil, LoginError{}
				}
				id = convertStrToNum(u.ID)
			}
			item := Dict{}
			key := newKey(c, kind, id, nil)
			err = datastore.Get(c, key, item)
			if err != nil {
				if kind == "users" {
					u := user.Current(c)
					if id == "me" || id == convertStrToNum(u.ID) {
						return User(*u), nil
					}
				}
				return nil, AppError{"No model found with that Id."}
			}
			return item, nil
		}
	case "POST", "PUT", "DELETE":
		u := user.Current(c)
		if u == nil {
			return nil, LoginError{}
		}
		switch r.Method {
		case "POST", "PUT":
			data, err := ParseBody(r)
			var key *datastore.Key
			if id == "" {
				if _id, exists := data["Id"]; exists {
					id = fmt.Sprintf("%s", _id)
				}
				key = datastore.NewIncompleteKey(c, kind, nil)
			}
			// verify data
			// verify and inject owners
			owner, _ := convertNumToStr(u.ID)
			data["owners"] = []interface{}{owner}
			if id != "" {
				key = newKey(c, kind, id, nil)
				err = isOwner(c, u, key)
				if err != nil {
					return nil, err
				}
			}
			key, err = datastore.Put(c, key, data)
			if err != nil {
				return nil, err
			}
			// TODO: this doesn't work need to set the Id properly with string or int
			data["Id"] = key.IntID()
			return data, nil
		case "DELETE":
			key := newKey(c, kind, id, nil)
			err = isOwner(c, u, key)
			if err != nil {
				return nil, err
			}
			err = datastore.Delete(c, key)
			if err != nil {
				return nil, err
			}
			return Dict{}, nil
		}
	}
	return nil, AppError{"Undefined method."}
}

type User user.User

func (u User) Write(c appengine.Context, w http.ResponseWriter) {
	w.Header().Set("content-type", "application/json")
	encoder := json.NewEncoder(w)
	id, _ := convertNumToStr(u.ID)
	encoder.Encode(Dict{
		"Id":    id,
		"email": u.Email,
	})
}

func init() {
	http.HandleFunc("/api/", Json(Restful))
}
