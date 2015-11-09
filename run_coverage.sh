#!/usr/bin/env bash

coverage report -m
coverage html -d $CIRCLE_ARTIFACTS
[[ ! -z "$$COVERALLS_REPO_TOKEN" ]] && coveralls || true;
