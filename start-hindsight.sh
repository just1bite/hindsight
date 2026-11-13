#!/bin/bash
set -e
cd /home/fahri/Downloads/0d50d41b-1392-4ceb-b761-2bd19d758f1c/finish/hindsight
export HINDSIGHT_API_LLM_PROVIDER=openai
export HINDSIGHT_API_LLM_API_KEY=$(grep '^HINDSIGHT_API_LLM_API_KEY=' .env | cut -d= -f2-)
export HINDSIGHT_API_LLM_MODEL=gpt-4o-mini
exec /home/fahri/.local/bin/uv run hindsight-api
