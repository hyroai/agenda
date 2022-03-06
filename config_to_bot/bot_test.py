import os
from typing import Dict, Tuple

import gamla

import agenda
from config_to_bot import yaml_to_bot

_PIZZA_YAML = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "examples/pizza/pizza.yaml"
)


async def _remote_function(url: str, params: Dict):
    del url
    name, amount_of_pizzas, toppings, size, address, phone, email = (
        params["name"],
        params["amount_of_pizzas"],
        params["toppings"],
        params["size"],
        params["address"],
        params["phone"],
        params["email"],
    )

    def topping_render(toppings: Tuple[str, ...]):
        if len(toppings) == 1:
            return f" with {toppings[0]}"
        if len(toppings) > 1:
            str_of_toppings = ", ".join(toppings[:-1])
            return f" with {str_of_toppings}, and {toppings[-1]}"
        return ""

    if (
        name
        and amount_of_pizzas
        and size
        and address
        and phone
        and email
        and toppings is not None
    ):
        return f"Thank you {name}! I got your phone: {phone}, and your email: {email}. We are sending you {int(amount_of_pizzas)} {size} pizzas{topping_render(toppings)} to {address}."
    return None


def _make_test(path: str, convos):
    with open(path) as f:
        yaml_string = f
        return agenda.expect_convos(
            convos, gamla.just(yaml_to_bot.yaml_to_cg(_remote_function)(yaml_string))
        )


test_pizza_intent_detection = _make_test(
    _PIZZA_YAML, [[["I want pizza", "Got it. Are you vegan?"]]]
)

test_skip_toppings_question = _make_test(
    _PIZZA_YAML,
    [
        [
            ["hi", "Would you like to order pizza?"],
            ["yes I want pizza with olives", "Got it. Are you vegan?"],
            ["no", "Got it. What is your name?"],
            ["Yoni", "Nice to meet you Yoni! How many pies would you like?"],
            ["4", "Got it. What pizza size would you like?"],
        ]
    ],
)

test_happy_flow = _make_test(
    _PIZZA_YAML,
    [
        [
            ["hi", "Would you like to order pizza?"],
            ["yes, I want pizza", "Got it. Are you vegan?"],
            ["no", "Got it. What is your name?"],
            ["Yoni", "Nice to meet you Yoni! How many pies would you like?"],
            ["4", "Got it. What kind of toppings would you like?"],
            ["mushrooms and olives", "Got it. What pizza size would you like?"],
            ["small", "Got it. What is your address?"],
            ["881 Mill Street Greenville SC", "Got it. What is your phone number?"],
            ["9998887777", "Got it. What is your email?"],
            [
                "abcd1234@gmail.com",
                "Got it. Thank you Yoni! I got your phone: 9998887777, and your email: abcd1234@gmail.com. We are sending you 4 small pizzas with mushrooms, and olives to 881 Mill Street Greenville SC.",
            ],
        ]
    ],
)

test_happy_flow_without_toppings = _make_test(
    _PIZZA_YAML,
    [
        [
            ["hi", "Would you like to order pizza?"],
            ["yes, I want pizza", "Got it. Are you vegan?"],
            ["no", "Got it. What is your name?"],
            ["Yoni", "Nice to meet you Yoni! How many pies would you like?"],
            ["4", "Got it. What kind of toppings would you like?"],
            ["none", "Got it. What pizza size would you like?"],
            ["small", "Got it. What is your address?"],
            ["881 Mill Street Greenville SC", "Got it. What is your phone number?"],
            ["9998887777", "Got it. What is your email?"],
            [
                "abcd1234@gmail.com",
                "Got it. Thank you Yoni! I got your phone: 9998887777, and your email: abcd1234@gmail.com. We are sending you 4 small pizzas to 881 Mill Street Greenville SC.",
            ],
        ]
    ],
)


test_happy_flow_wihtout_asking_for_amount_and_size = _make_test(
    _PIZZA_YAML,
    [
        [
            ["hi", "Would you like to order pizza?"],
            ["yes, I want 2 large pizzas with mushrooms", "Got it. Are you vegan?"],
            ["no", "Got it. What is your name?"],
            ["Yoni", "Nice to meet you Yoni! What is your address?"],
            ["881 Mill Street Greenville SC", "Got it. What is your phone number?"],
            ["9998887777", "Got it. What is your email?"],
            [
                "abcd1234@gmail.com",
                "Got it. Thank you Yoni! I got your phone: 9998887777, and your email: abcd1234@gmail.com. We are sending you 2 large pizzas with mushrooms to 881 Mill Street Greenville SC.",
            ],
        ]
    ],
)
