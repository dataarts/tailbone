package tailbone

import (
  "net/http"
  "fmt"
)

func restful(w http.ResponseWriter, r *http.Request) {
  fmt.Fprintf(w, "<html><body>hi</body></html>")
}

func init() {
  http.HandleFunc("/", restful)
}
