#!/usr/bin/env bash
TARGET="${1:-{right-of}}"

# Strip // comments, collapse newlines into spaces, and load into tmux buffer
sed 's|//.*$||' | tr '\n' ' ' | tmux load-buffer -b sclang_buf -

tmux paste-buffer -d -b sclang_buf -t "$TARGET"
tmux send-keys -t "$TARGET" C-m
