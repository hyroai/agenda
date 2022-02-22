const express = require("express");
const app = express();

const listen = ({ incoming_utterance }) =>
  incoming_utterance.includes("hello") ||
  incoming_utterance.includes("Hello") ||
  null;

app.use(express.json());

app.post("/listen-hello", (req, res) => {
  console.log("Got a POST request for /listen-hello");
  res.json(listen(req.body));
});

const server = app.listen(8000, () => {
  const host = server.address().address;
  const { port } = server.address();

  console.log("Example app listening at http://%s:%s", host, port);
});
