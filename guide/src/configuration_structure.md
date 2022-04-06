# Configuration structure

`Agenda` configurations are written in yaml files, the only thing which is nontrivial about yaml files is the usage of `*` and `&` which defines some variable and then use it inline. So if you see `*something` then you know somehere there should be `&something` that defines what it means.

The configuration is built of 3 parts: `actions`, `knowledge` and `slots`.

## `knowledge`

Currently supports questions and answers.

```yaml
knowledge:
  - faq:
      - question: What is your opening hours?
        answer: 2pm to 10pm every day.
```

## `actions`

The `actions` part lists what the bot can do on behalf of the user. When deciding what to say, the bot will try to match the first relevant action, fulfill its dependencies and performing it, either a saying something or calling a remote API.

Actions might have some dependencies, defined under the `needs` section.

In addition - it might not make sense to do some things unless some conditions are met. This is what the `when` section is for.

For example:

```yaml
actions:
  - say: I can only help with pizza reservations.
    when:
      not: *wants-pizza
  - say:
      url: http://localhost:8000/order-pizza
    when: *wants-pizza
    needs:
      - key: toppings
        value:
            ask: What kind of toppings would you like?
            multiple-choice:
                - mushrooms
                - olives
                - tomatoes
                - onions
      - key: size
        value:
            ask: What pizza size would you like?
            choice:
                - small
                - medium
                - large
```

## `slots`

If you have a value that is recurring in more than one place, you can factor it out to the `slots` section.

```yaml
slots:
  - &wants-pizza
    ask: Would you like to order pizza?
    type: boolean

actions:
  - say: I can only help with pizza reservations.
    when:
      not: *wants-pizza
  - say: you want pizza!
    when: *wants-pizza
```

### Types of slots

Currently supported types:

#### Person name

```yaml
&name
ack: Nice to meet you {}!
ask: What is your name?
type: name
```

#### Address

```yaml
&address
ask: What is your address?
type: address
```

#### Phone

```yaml
&phone
ask: What is your phone number?
type: phone
```

#### Email

```yaml
&email
ask: What is your email?
type: email
```

#### Amount of

```yaml
&amount_of_something
ask: How many dogs do you have?
amount-of: dogs
```

#### Boolean

```yaml
&user-wants-pizza
ask: Would you like to order pizza?
type: boolean
```

#### Intent

```yaml
&user-wants-to-complain
intent:
  - I have a complaint
  - I want to complain
```

#### Choice

```yaml
&size-of-shirt
ask: What size of t-shirt would you like?
choice:
  - small
  - medium
  - large
```

#### Multiple choice

```yaml
&choice-of-toppings
ask: What kind of toppings would you like?
multiple-choice:
  - mushrooms
  - olives
  - tomatoes
  - onions
```

### Compound slots

Slots can be combined into compound slots via operators.

List of available operators:

- `not`
- `all`
- `any`
- `greater_equals`
- `equals`

For example:

```yaml
slots:
  - &age
    ask: What is your age?
    type: number
  - &gender
    ask: What is your gender?
    multiple-choice:
      - male
      - female
      - non binary
  - &male_and_above_18
    all:
      - is: age
        greater_than: 18
      - is: gender
        equals: female
```
