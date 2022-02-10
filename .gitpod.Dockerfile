FROM  gitpod/workspace-full

USER gitpod

RUN sudo apt-get install -yq python3-dev graphviz graphviz-dev
RUN pyenv update
RUN pyenv install 3.9.10
RUN pyenv global 3.9.10
RUN python -m pip install --no-cache-dir --upgrade pip
RUN echo "alias pip='python -m pip'" >> ~/.bash_aliases

RUN python -m pip install spacy
RUN python -m spacy download en_core_web_lg

# `duckling` compatbility issue.
RUN python -m pip install --force-reinstall JPype1==0.6.3
