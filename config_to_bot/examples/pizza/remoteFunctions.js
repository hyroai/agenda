const express = require("express");
const app = express();
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
        `Thank you ${name}! I got your phone: ${phone}, and your email: ${email}. We are sending you ${amount_of_pizzas} ${size} pizzas with ${toppings} to ${address}.`
      );
    } else {
      res.json(null);
    }
  }
);
const port = 8000;
app.listen(port, () => console.log(`Example app listening at post ${port}`));
