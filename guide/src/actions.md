# `actions`

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