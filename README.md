# Agenda

`Agenda` is a declarative specification language for conversations, focused on the goals and dependencies, rather than sequential flows or conversation trees.

## Setup

```bash
git clone https://github.com/hyroai/agenda.git
pip install -e ./agenda
yarn install --cwd=./agenda/config_to_bot/debugger
```

In addition run `yarn install` in each example that you wish to run in `config_to_bot/examples`

### Issues with dependencies

- `spacy` requires to run: `python -m spacy download en_core_web_lg`

### Running pizza example

- Running remote functions server:

```
cd examples/pizza
yarn start
```

- Running bot's server: `python config_to_bot/main.py config_to_bot/examples/pizza/pizza.yaml`
- Running client:

```
cd debugger
yarn start
```

## Example

Let's imagine building a bot for pizza place. In terms of conversation trees, there are many options as to how this conversation can go, here are a couple of examples:

```
    👩 hi there

    🤖 Would you like to order pizza?

    👩 yup

    🤖 Alright. Are you vegan?

    👩 no I am not

    🤖 Cool. What is your name?

    👩 Alice

    🤖 Cool. How many pies would you like?

    👩 2

    🤖 Okay. What kind of toppings would you like?

    👩 mushrooms

    🤖 Cool. What pizza size would you like?

    👩 large

    🤖 Cool. What is your address?

    👩 881 Mill Street Greenville SC

    🤖 Got it. What is your phone number?

    👩 212 222 2222

    🤖 Alright. What is your email?

    👩 alice@gmail.com

    🤖 Cool. Thank you Alice! I got your phone: 212 222 2222, and your email: alice@gmail.com. We are sending you 2 large pizzas with mushrooms to 881 Mill Street Greenville SC.
```

```
    👩 Hi!

    🤖 Would you like to order pizza?

    👩 yes

    🤖 Alright. Are you vegan?

    👩 nope

    🤖 Cool. What is your name?

    👩 Alice, my address is 881 Mill Street Greenville SC

    🤖 Cool. How many pies would you like?

    👩 2 large pizzas with mushrooms

    🤖 Cool. What is your phone number?

    👩 212 222 2222

    🤖 Okay. What is your email?

    👩 alice@gmail.com

    🤖 Okay. Thank you Alice! I got your phone: 212 222 2222, and your email: alice@gmail.com. We are sending you 2 large pizzas with mushrooms to 881 Mill Street Greenville SC.
```

Collecting data or making up transcriptions to cover all the options, even with machine learning is a pretty tedious task, and would be hard to maintain over time.

Instead one would prefer to say what **is needed** to order pizza:

```yaml
definitions:
  - &name
    ask: What is your name?
    listen:
      type: name
  - &address
    ask: What is your address?
    listen:
      type: address
  - &phone
    ask: What is your phone number?
    listen:
      type: phone
  - &email
    ask: What is your email?
    listen:
      type: email
  - &amount_of_pizzas
    ask: How many pies would you like?
    amount-of: pie
  - &wants-pizza-question
    ask: Would you like to order pizza?
    listen:
      type: bool
  - &wants-pizza-intent
    listen:
      type: intent
      examples:
        - I want to order pizza
        - I want pizza
  - &wants-pizza
    any:
      - *wants-pizza-question
      - *wants-pizza-intent
  - &is-vegan
    ask: Are you vegan?
    listen:
      type: bool
  - &toppings
    ask: What kind of toppings would you like?
    listen:
      type: multiple-choice
      options:
        - mushrooms
        - olives
        - tomatoes
  - &size
    ask: What pizza size would you like?
    listen:
      type: single-choice
      options:
        - small
        - medium
        - large
goals:
  - say: I'm transferring you to an agent.
    when:
      not: *wants-pizza
  - say: We currently do not sell vegan pizzas.
    when:
      all:
        - *wants-pizza
        - *is-vegan
  - say:
      url: http://localhost:8000/order-pizza
    needs:
      - key: name
        value: *name
      - key: amount_of_pizzas
        value: *amount_of_pizzas
      - key: toppings
        value: *toppings
      - key: size
        value: *size
      - key: address
        value: *address
      - key: phone
        value: *phone
      - key: email
        value: *email
    when:
      all:
        - *wants-pizza
        - not: *is-vegan
```

Given this spec, agenda will create a bot that can handle the conversations above, and many other variations. **No custom training or data collection is needed**, and if requirements change, all the conversation designer needs to do is change the configuration.

For Joe's pizza place, the actual API that orders the pizza is not a part of the bot code, so it is convenient to do this in an external server for the user to define. This allows combining agenda with any backend coding language, or use multiple backends within the same bot.

## Features summary

- Use remote servers for some of the bot parts (e.g. fulfill some request or recognize an intent).
- Automatic acking when new information is received.
- Built-in support to listening to emails, dates, times, names, amounts and booleans.
