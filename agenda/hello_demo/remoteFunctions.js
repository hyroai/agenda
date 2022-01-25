var express = require("express");
var app = express();

const listen = ({ incoming_utterance }) =>
  incoming_utterance.includes("hello") ||
  incoming_utterance.includes("Hello") ||
  null;

app.use(express.json());

app.post("/listen-hello", function (req, res) {
  console.log("Got a POST request for /listen-hello");
  res.json(listen(req.body));
});

app.post("/order-pizza", function (req, res) {
  console.log("Got a POST request for /order-pizza");
  if (!req.body.phone || !req.body.email || !req.body.amount_of_pizzas || !req.body.name || !req.body.address || !req.body.size || !req.body.toppings) {
    res.json(null);
  } else {
    res.json(
      `Thank you ${req.body.name}! I got your phone: ${req.body.phone}, and your email: ${req.body.email}. We are sending you ${req.body.amount_of_pizzas} ${req.body.size} pizzas to ${req.body.address}.`
    );
  }
});

var server = app.listen(8000, function () {
  var host = server.address().address;
  var port = server.address().port;

  console.log("Example app listening at http://%s:%s", host, port);
});
