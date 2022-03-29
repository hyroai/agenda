`Agenda` is a declarative specification language for conversations, focused on specifying knowledge and actions, rather than sequential flows or conversation trees.

We attempt to answer the question - what would a conversation AI framework look like if it were strapped down to the minimum possible requirements - the things you'd have to tell your agent even if it were human.

These requirements would be the bot's actions and knowledge.

- Actions - what can the bot actually achieve in the world on behalf of the user. This is usually done via foreign APIs which the bot can call. Example: "The bot can order a pizza by calling http://order.com/pizza and has to give a phone, address and pizza_size".
- Knowledge - what does the bot know and will be able to let the users interacting with it know. Example: "The bot should know that our opening hours are 2pm to 10pm.".

Given a specification of knowledge and actions, Agenda will transform them into a bot that can interact with users, helping them access its actions and knowledge.

This is how a specification looks like:

```yaml
knowledge:
  - question: what are your opening hours?
    answer: 2pm to 10pm.
  ...
actions:
  - url: http://order.com/pizza
    when:
      intent:
        - I want to order pizza
        - I want pizza
    needs:
      - key: phone
        value:
          type: phone
          ask: At what number can we reach you?
      ...
```

As much as possible, we try to avoid having the user need to give different formulations and phrasings as we believe NLP has reached a point where this is no longer required.

We optimize on:

- composability; actions and knowledge can be disabled or enabled and don't interfere with each other
- reuse; bots can share a part of their configuration
- focus on business logic rather than NLP; no training examples.

## Video introduction

[![Here](https://img.youtube.com/vi/67BXS5A6WLY/default.jpg)](https://www.youtube.com/watch?v=67BXS5A6WLY)

## Target audience

`Agenda` is ideal for general purpose developers who want to set up a conversational interface and are not looking to start an NLP research project, or train their own models. The bots produced will communicate by text via a socket run by a python server, so can be embedded in any service in a short time.

That said those who want to leverage existing NLP services (e.g. an intent recognition service) can embed them within the configuration. This would look like this:

```
...

&my-custom-intent-recognizer
  url: http://localhost:8000/listen-hello
  needs:
    - key: incoming_utterance
      value: incoming_utterance
...

```

## Setup

```bash
git clone https://github.com/hyroai/agenda.git
pip install -e ./agenda
yarn install --cwd=./config_to_bot/debugger
```

In addition run `yarn install` in each example that you wish to run in `config_to_bot/examples`

### Issues with dependencies

- `spacy` requires to run: `python -m spacy download en_core_web_sm`

### Running pizza example

- Running remote functions server:

```
cd ./agenda/config-to-bot/examples/pizza
yarn install
yarn start
```

- Running bot's server: `python config_to_bot/main.py`
- Running bot designer:

```
cd ./config_to_bot/debugger
yarn install
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

Instead one would prefer to say what **is needed** to order pizza, alongside the other goals of the conversation.

```yaml
actions:
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

Subsequently we can define how to ask and listen to each one of the needed details.

```yaml
slots:
  - &name
    ack: Nice to meet you {value}!
    ask: What is your name?
    type: name
  - &address
    ask: What is your address?
    type: address
  - &phone
    ask: What is your phone number?
    type: phone
  - &email
    ask: What is your email?
    type: email
  - &amount_of_pizzas
    ask: How many pies would you like?
    amount-of: pie
  - &wants-pizza-question
    ask: Would you like to order pizza?
    type: boolean
  - &wants-pizza-intent
    intent:
      - I want to order pizza
      - I want pizza
  - &wants-pizza
    any:
      - *wants-pizza-question
      - *wants-pizza-intent
  - &is-vegan
    ask: Are you vegan?
    type: boolean
  - &toppings
    ask: What kind of toppings would you like?
    multiple-choice:
      - mushrooms
      - olives
      - tomatoes
      - onions
  - &size
    ask: What pizza size would you like?
    choice:
      - small
      - medium
      - large
```

Given this spec, agenda will create a bot that can handle the conversations above, and many other variations. **No custom training or data collection is needed**, and if requirements change, all the conversation designer needs to do is change the configuration.

For Joe's pizza place, the actual API that orders the pizza is not a part of the bot code, so it is convenient to do this in an external server for the user to define. This allows combining agenda with any backend coding language, or use multiple backends within the same bot.
