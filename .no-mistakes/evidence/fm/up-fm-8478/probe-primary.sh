#!/usr/bin/env bash
set -eu
EVIDENCE=~/.no-mistakes/evidence/01M7EFPKVWB34HQDAX5PBSK5QB
LAB=$(mktemp -d "$EVIDENCE/p.XXXXXX")
cleanup() {
  if [ -d "$LAB/tmux" ]; then
    TMUX_TMPDIR="$LAB/tmux" tmux -L fm-lab kill-server 2>/dev/null || true
  fi
  rm -rf -- "$LAB"
}
trap cleanup EXIT
bin/fm-lab-home.sh create "$LAB"
mkdir -p "$LAB/tmux"
touch "$LAB/config/supervision-host"
env -u NO_MISTAKES_GATE -u FM_GATE_REFUSE_BYPASS -u FM_ROOT_OVERRIDE -u FM_STATE_OVERRIDE -u FM_DATA_OVERRIDE -u FM_CONFIG_OVERRIDE -u FM_PROJECTS_OVERRIDE TMUX_TMPDIR="$LAB/tmux" tmux -L fm-lab new-session -d -x 120 -y 40 -s primary -c "$PWD" -e FM_HOME="$LAB" claude
sleep 6
TMUX_TMPDIR="$LAB/tmux" tmux -L fm-lab display-message -p -t primary 'grid=#{pane_width}x#{pane_height} pid=#{pane_pid}'
TMUX_TMPDIR="$LAB/tmux" tmux -L fm-lab capture-pane -p -t primary
