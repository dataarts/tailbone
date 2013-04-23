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
	"appengine/blobstore"
	"appengine/image"
	"encoding/json"
	"net/http"
)

type BlobKey appengine.BlobKey

func (blob BlobKey) Write(c appengine.Context, w http.ResponseWriter) {
	blobstore.Send(w, appengine.BlobKey(blob))
}

type blobInfoList map[string][]*blobstore.BlobInfo

func (blobs blobInfoList) Write(c appengine.Context, w http.ResponseWriter) {
	resp := DictList{}
	for _, bloblist := range blobs {
		for _, blob := range bloblist {
			d := Dict{
				"Id":           string(blob.BlobKey),
				"filename":     blob.Filename,
				"content_type": blob.ContentType,
				"size":         blob.Size,
				"creation":     blob.CreationTime.Unix(),
			}
			if re_image.MatchString(blob.ContentType) {
				url, err := image.ServingURL(c, blob.BlobKey, nil)
				if err == nil {
					d["image_url"] = url.String()
				}
			}
			resp = append(resp, d)
		}
	}
	w.Header().Set("content-type", "application/json")
	encoder := json.NewEncoder(w)
	encoder.Encode(resp)
}

func Files(c appengine.Context, r *http.Request) (ResponseWritable, error) {
	_, id, err := ParseRestfulPath(r.URL.Path)
	if err != nil {
		return nil, err
	}
	switch r.Method {
	case "GET":
		if id == "" {
			uploadURL, err := blobstore.UploadURL(c, "/api/files/upload", nil)
			if err != nil {
				return nil, err
			}
			return Dict{
				"upload_url": uploadURL.String(),
			}, nil
		}
		return BlobKey(appengine.BlobKey(id)), nil
	case "POST":
		if id == "upload" {
			blobs, _, err := blobstore.ParseUpload(r)
			if err != nil {
				return nil, err
			}
			return blobInfoList(blobs), nil
		}
		return nil, AppError{"You must make a GET call to /api/files to get a POST url."}
	case "DELETE":
		err = blobstore.Delete(c, appengine.BlobKey(id))
		if err != nil {
			return nil, err
		}
		return Dict{}, nil
	}
	return nil, AppError{"Undefined method."}
}

func init() {
	http.HandleFunc("/api/files/", Json(Files))
}
