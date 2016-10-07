#!/usr/bin/env bash

coverage run --source=django_sharding,django_sharding_library ./runtests.py
coverage report -m
coverage html -d $CIRCLE_ARTIFACTS
[[ ! -z "$$COVERALLS_REPO_TOKEN" ]] && coveralls || true;
