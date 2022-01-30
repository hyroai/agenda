const express = require("express");
const app = express();

app.use(express.json());

app.post("/order-pizza", function ({ body }, res) {
  console.log("Got a POST request for /order-pizza");
  if (
    !body.phone ||
    !body.email ||
    !body.amount_of_pizzas ||
    !body.name ||
    !body.address ||
    !body.size ||
    !body.toppings
  ) {
    res.json(null);
  } else {
    res.json(
      `Thank you ${body.name}! I got your phone: ${body.phone}, and your email: ${body.email}. We are sending you ${body.amount_of_pizzas} ${body.size} pizzas to ${body.address}.`
    );
  }
});

const server = app.listen(8000, function () {
  const host = server.address().address;
  const port = server.address().port;

  console.log("Example app listening at http://%s:%s", host, port);
});
