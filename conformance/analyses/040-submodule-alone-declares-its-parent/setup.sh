# The remote lib: a bare repository whose one commit holds an astra.yaml
# that declares its parent with .. and reads the parent's input1, cloned
# from a repository made beside it, which then goes.
lib=$ASTRA_CASE_REMOTES/lib
git init --quiet "$lib.work"
cat > "$lib.work/astra.yaml" <<'EOF'
spec_version: "0.1.0"
analyses:
  parent:
    path: ..
outputs:
  result:
    type: metric
    format: json
    inputs: [parent.input1]
    recipe:
      command: python make.py '{inputs.parent.input1}' '{output}'
EOF
git -C "$lib.work" add astra.yaml
git -C "$lib.work" commit --quiet --message lib
git clone --quiet --bare "$lib.work" "$lib"
rm -rf "$lib.work"

# The analysis's repository, with lib added as a submodule.
git init --quiet
git submodule add --quiet "file://$lib" lib
git add --all
git commit --quiet --message files
