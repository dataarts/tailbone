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
	"appengine/channel"
	"encoding/json"
	"io/ioutil"
	"math/rand"
	"net/http"
)

const (
	letters  = "abcdefghijklmnopqrstuvwxyz"
	nletters = len(letters)
)

func createId(size int) string {
	b := make([]byte, size)
	for x := 0; x < size; x++ {
		b[x] = letters[rand.Intn(nletters)]
	}
	return string(b)
}

func Messages(c appengine.Context, r *http.Request) (ResponseWritable, error) {
	switch r.Method {
	case "GET":
		var clientId = createId(4)
		token, err := channel.Create(c, clientId)
		if err != nil {
			return nil, err
		}
		return Dict{
			"client_id": clientId,
			"token":     token,
		}, nil
	case "POST":
		defer r.Body.Close()
		body, err := ioutil.ReadAll(r.Body)
		if err != nil {
			return nil, err
		}
		var data Dict
		err = json.Unmarshal(body, &data)
		if err != nil {
			return nil, err
		}
		if to, ok := data["to"].(string); ok {
			channel.Send(c, to, string(body))
			return Dict{}, nil
		}
		return nil, AppError{"Must provide a 'to' client_id."}
	}
	return nil, AppError{"Undefined method."}
}

func init() {
	http.HandleFunc("/api/messages/", Json(Messages))
}
