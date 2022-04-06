# Configuration basics

`Agenda` configurations are written in yaml files, the only thing which is nontrivial about yaml files is how variables work. Variable is defined using `&`, as in `&my-variable` and are dereferenced using `*`, e.g. `*my-variable` (basically a glorified copy paste).

The configuration is built of 3 main parts: `actions`, `knowledge` and `slots`, and an additional part to debugging - `debug`.
