const express = require("express");

const app = express();

const renderToppings = (toppings) =>
  toppings.length == 1
    ? `with ${toppings}`
    : toppings.length > 1
    ? `with ${toppings.slice(0, -1).join(", ")}, and ${
        toppings[toppings.length - 1]
      }`
    : "";

app.use(express.json());

const validateRequest = ({
  phone,
  email,
  amount_of_pizzas,
  name,
  address,
  size,
  toppings,
}) => phone && email && amount_of_pizzas && name && address && size && toppings;

const renderSuccess = ({
  name,
  phone,
  email,
  address,
  amount_of_pizzas,
  size,
}) =>
  `Thank you ${name}! I got your phone: ${phone}, and your email: ${email}. We are sending you ${amount_of_pizzas} ${size} pizzas ${renderToppings(
    toppings
  )} to ${address}.`;

app.post("/order-pizza", ({ body }, res) => {
  res.json(validateRequest(body) ? renderSuccess(body) : null);
});

const port = process.env.PORT || 8000;

app.listen(port, () => console.log(`app listening at post ${port}`));
