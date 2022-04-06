# `debug`

This part can be used in conjunction with the debugger UI to peek into the bot's state.

When using it you need to label the subgraph you are watching like so:

```yaml
debug:
  - key: some-label-for-the-slot-below
    value: *my-slot
  - key: some-other-label
    value: *another-slot
```

The result shows the value the bot has in store at that moment of the conversation, alongisde what this part of the bot wants to say (not all parts participate every turn). You'll see a small checkmark if the bot-part has participated in the last turn.
