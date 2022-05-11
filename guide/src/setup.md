# Setup

You can use `agenda` on your own machine, or use the version hosted by Hyro at agenda.hyro.ai.

```bash
git clone https://github.com/hyroai/agenda.git
pip install -e ./agenda
pip install cloud-utils@https://github.com/hyroai/cloud-utils/tarball/master
yarn install --cwd=./config_to_bot/debugger
```

In addition run `yarn install` in each example that you wish to run in `config_to_bot/examples`

## Issues with dependencies

- `spacy` requires to run: `python -m spacy download en_core_web_sm`

## Running pizza example

- Running remote functions server:

```bash
cd ./agenda/config-to-bot/examples/pizza
yarn install
yarn start
```

- Running bot's server: `python config_to_bot/main.py`
- Running bot designer:

```bash
cd ./config_to_bot/debugger
yarn install
yarn start
```
