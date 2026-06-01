#!/bin/bash
# Reproduce the paper's results end-to-end.
#
# This script runs inside the compute container. The method runner emits
# proposed compiler outputs and the ground-first baseline in one artifact,
# then calls scripts/evaluate.sh to score all methods from that artifact.
#
# Assumes:
#   - Container is built (environment/container.sif)
#   - Data and models are downloaded (via scripts/download.sh)
#   - Working directory is /home/user
#
# This is the "gold standard" reproduction — 
# You do not need to run this, but keep this in good shape
# so other agents can easily run a full loop of reproduction and get the paper's numbers.

set -e

cd /home/user

bash scripts/method.sh
