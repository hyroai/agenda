# Configuration structure

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

Actions list what the bot can do on behalf of the user. When deciding what to say, the bot will try to match the first relevant action, fulfill its dependencies and performing it, either a saying something or calling a remote API.

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
