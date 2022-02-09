const express = require("express");
const app = express();

const listen = ({ incoming_utterance }) =>
  incoming_utterance.includes("hello") ||
  incoming_utterance.includes("Hello") ||
  null;

app.use(express.json());

app.post("/listen-hello", function (req, res) {
  console.log("Got a POST request for /listen-hello");
  res.json(listen(req.body));
});

const server = app.listen(8000, function () {
  const host = server.address().address;
  const port = server.address().port;

  console.log("Example app listening at http://%s:%s", host, port);
});
