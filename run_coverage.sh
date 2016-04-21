#!/usr/bin/env bash

[[ ! -z "$$COVERALLS_REPO_TOKEN" ]] && coveralls || true;
