start_shell_tree() {  # <dir> <leaf-name>
  local dir=$1 leaf=$2 i=0
  mkdir -p "$dir/tree"
  ln -sf "$(command -v sleep)" "$dir/tree/$leaf"
  cat >"$dir/tree/wrapper" <<'SH'
#!/usr/bin/env bash
"$1" "$2"
exit $?
SH
  chmod +x "$dir/tree/wrapper"
  bash -c '"$1" "$2" "$3" & wait' root "$dir/tree/wrapper" "$dir/tree/$leaf" "$FM_TEST_STUB_MAX_BLOCK_SECONDS" >/dev/null 2>&1 &
  TREE_ROOT=$!
  TREE_LEAF=
  while [ -z "$TREE_LEAF" ] && [ "$i" -lt 50 ]; do
    TREE_LEAF=$(ps -axo pid=,args= | awk -v p="$dir/tree/$leaf" '$2 == p { print $1; exit }')
    [ -n "$TREE_LEAF" ] || sleep 0.1
    i=$((i + 1))
  done
  [ -n "$TREE_LEAF" ] || fail "the $leaf fixture process never started"
}

