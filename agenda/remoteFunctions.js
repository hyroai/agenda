var express = require("express");
var app = express();

app.get("/listen-yes", function (req, res) {
  console.log("Got a GET request for /listen-yes");
  const listen = (req) => {
    let result;
    if (req.includes("yes") || req.includes("Yes")) {
      result = true;
    } else {
      result = false;
    }
    return result;
  };
  res.send(listen);
});

var server = app.listen(8000, function () {
  var host = server.address().address;
  var port = server.address().port;

  console.log("Example app listening at http://%s:%s", host, port);
});
