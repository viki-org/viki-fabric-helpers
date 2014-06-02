#!/bin/bash

cd docs && \
  ([ -d venv/ ] || virtualenv venv) && \
  . venv/bin/activate && \
  pip install -r requirements.txt && \
  make html && \
  deactivate
