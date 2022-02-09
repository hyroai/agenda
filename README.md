# Agenda

## Setup

```
git clone https://github.com/hyroai/agenda.git
cd agenda
pip install -e .
cd config_to_bot/debugger
npm install

```
In addition run `npm install` in each example that you wish to run in `/examples`

## Intro

`Agenda` is a declarative specification language for conversations, focused on the goals and dependencies, rather than sequential flows or conversation trees.

For example, let's assume we are building a bot for pizza place. In terms of conversation trees, there are many options as to how this conversation can go, here are a couple of examples:

```
User: hi there
Bot: Would you like to order pizza?
User: yes
Bot: Got it. What is your name?
User: yoni
Bot: Got it. How many pies would you like?
User: 4
Bot: Got it. What is your address?
User: 881 Mill Street Greenville South Carolina
Bot: Got it. What is your phone number?
User: 2345345345
Bot: Got it. What is your email?
User: sdfsdf@gmail.com
Bot: Got it. Thank you Yoni! I got your phone: 2345345345, and your email: sdfsdf@gmail.com. We are sending you 4 pizzas to 881 Mill Street Greenville South Carolina.
```

```
User: i want pizza
Bot: "Got it. What is your name?"
User: yoni and my address is 881 Mill Street Greenville South Carolina
Bot: "Got it. How many pies would you like?"
User: 4
Bot: "Got it. What is your phone number?"
User: 234234234
Bot: "Got it. What is your email?"
User: sdfs@gmail.com
Bot: "Got it. Thank you Yoni! I got your phone: 234234234, and your email: sdfs@gmail.com. We are sending you 4 pizzas to 881 Mill Street Greenville South Carolina."
```

Collecting data or making up transcriptions to cover all the options, even with machine learning is a pretty tedious task, and would be hard to maintain over time.

Instead one would prefer to say what **is needed** to order pizza:

```yaml
definitions:
  - &wants-to-order-pizza
    ask: Would you like to order pizza?
    listen:
      type: bool
      examples:
        - I want to order pizza
        - I want pizza
goals:
  - say:
      url: http://localhost:8000/order-pizza # Actually ordering a pizza and sending back a confirmation will happen through an external API!
    when: *wants-to-order-pizza
    needs:
      - key: name
        value:
          ask: What is your name?
          listen:
          type: name
      - key: amount_of_pizzas
        value:
          ask: How many pies would you like?
          listen:
          type: amount
      - key: address
        value:
          ask: What is your address?
          listen:
          type: address
      - key: phone
        value:
          ask: What is your phone number?
          listen:
          type: phone
      - key: email
        value:
          ask: What is your email?
          listen:
          type: email
  - say: Sorry, I can only help with ordering pizza.
    when:
      complement: *wants-to-order-pizza
```

Given this spec, agenda will create a bot that can handle the conversations above, and many other variations. **No custom training or data collection is needed**, and if requirements change, all the conversation designer needs to do is change the configuration.

For Joe's pizza place, the actual API that orders the pizza is not a part of the bot code, so it is convenient to do this in an external server for the user to define. This allows combining agenda with any backend coding language, or use multiple backends within the same bot.

## Features:

- Remote functions: Using remote servers for some of the bot parts.
- Acknowledgement: the bot will ack information it received automatically and naturally, with no need to specify this.
- All utterances are fully configurable.
- Many built-in functions to support collection of emails, dates, times, names, amounts booleans etc'...

## Running pizza example:

- Running remote functions server:

```
cd examples/pizza
npm start
```

- Running bot's server: `python main.py {path-to-pizza-yaml-file}`
- Running client:

```
cd debugger
npm start
```
