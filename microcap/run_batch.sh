#!/bin/bash
# Microcap Hunt — batch runner
# Called by system cron every 15 minutes
cd /home/openclaw/.openclaw/workspace/microcap
python3 main.py --batch-size 25 --max 500 >> /home/openclaw/.openclaw/workspace/microcap/microcap_hunt.log 2>&1
