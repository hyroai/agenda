const express = require("express");
const app = express();
const renderToppings = (toppings) => {
  if (toppings.length == 1) {
    return `with ${toppings}`;
  }
  if (toppings.length > 1) {
    return `with ${toppings.slice(0, -1).join(", ")}, and ${
      toppings[toppings.length - 1]
    }`;
  } else {
    return ``;
  }
};
app.use(express.json());
app.post(
  "/order-pizza",
  (
    { body: { phone, email, amount_of_pizzas, name, address, size, toppings } },
    res
  ) => {
    console.log("Got a POST request for /order-pizza");
    if (
      phone &&
      email &&
      amount_of_pizzas &&
      name &&
      address &&
      size &&
      toppings
    ) {
      res.json(
        `Thank you ${name}! I got your phone: ${phone}, and your email: ${email}. We are sending you ${amount_of_pizzas} ${size} pizzas ${renderToppings(
          toppings
        )} to ${address}.`
      );
    } else {
      res.json(null);
    }
  }
);
const port = process.env.PORT || 8000;
app.listen(port, () => console.log(`Example app listening at post ${port}`));
