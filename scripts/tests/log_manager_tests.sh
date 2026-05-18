#!/usr/bin/env bash
# Backward-compatible alias for renamed maintenance wrapper.
set -euo pipefail

"$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/log_maintenance_tests.sh"
