# `Agenda`

`Agenda` is a declarative specification language for conversations, focused on specifying knowledge and actions, rather than sequential flows or conversation trees.

We imagine a conversational AI framework that is strapped down to the minimum possible requirements - the things you'd have to tell your agent even if it were human.

These requirements would be the bot's actions and knowledge.

- Actions - what effects can the bot have on the world. This is usually done via API calls. Example: "The bot can order a pizza by calling http://order.com/pizza and has to give a phone, address and pizza size".
- Knowledge - what the bot knows and will be able to let the users interacting with it know. Example: "The bot should know that our opening hours are 2pm to 10pm.".

Given the knowledge and actions, we create a bot that can interact with users, helping them perform actions and enabling access to knowledge. This means non-linear conversations, where the user can context switch without the bot forgetting its state - a stark difference from trying to come up with all the different paths a conversation could take, i.e. a conversation tree.

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

```yaml
# The service would receive a post request, e.g.`{someKey: "I want pizza"}`
&my-custom-intent-recognizer
remote:
  state-remote: http://localhost:8000/listen-wants-pizza
  needs:
    - key: someKey
      value: incoming_utterance
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
🤖 Got it. How many pies would you like?
👩 2
🤖 Okay. What kind of toppings would you like?
👩 mushrooms
🤖 Cool. What pizza size would you like?
👩 large
🤖 Cool. What is your address?
👩 81 Mill Street Greenville SC
🤖 Got it. What is your phone number?
👩 212 222 2222
🤖 Cool. Thank you Alice! The phone I got is 212 222 2222.
 We are sending you 2 large pizzas with mushrooms to 81 Mill Street Greenville SC.
```

```
👩 Hi!
🤖 Would you like to order pizza?
👩 yes
🤖 Alright. Are you vegan?
👩 nope
🤖 Cool. What is your name?
👩 Alice, my address is 81 Mill Street Greenville SC
🤖 Cool. How many pies would you like?
👩 2 large pizzas with mushrooms
🤖 Cool. What is your phone number?
👩 212 222 2222
🤖 Okay. Thank you Alice! The phone I got is 212 222 2222.
  We are sending you you 2 large pizzas with mushrooms to 81 Mill Street Greenville SC.
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
      say-remote: http://localhost:8000/order-pizza
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
