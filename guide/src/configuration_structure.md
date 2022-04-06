# Configuration structure

`Agenda` configurations are written in yaml files, the only thing which is nontrivial about yaml files is the usage of `*` and `&` which defines some variable and then use it inline. So if you see `*something` then you know somehere there should be `&something` that defines what it means.

The configuration is built of 3 main parts: `actions`, `knowledge` and `slots`, and an additional part to debugging - `debug`.
