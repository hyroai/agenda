# `slots`

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

## Types of slots

Currently supported types:

### Person name

```yaml
&name
ack: Nice to meet you {}!
ask: What is your name?
type: name
```

### Address

```yaml
&address
ask: What is your address?
type: address
```

### Phone

```yaml
&phone
ask: What is your phone number?
type: phone
```

### Email

```yaml
&email
ask: What is your email?
type: email
```

### Amount of

```yaml
&amount_of_something
ask: How many dogs do you have?
amount-of: dogs
```

### Boolean

```yaml
&user-wants-pizza
ask: Would you like to order pizza?
type: boolean
```

### Intent

```yaml
&user-wants-to-complain
intent:
  - I have a complaint
  - I want to complain
```

### Choice

```yaml
&size-of-shirt
ask: What size of t-shirt would you like?
choice:
  - small
  - medium
  - large
```

### Multiple choice

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
