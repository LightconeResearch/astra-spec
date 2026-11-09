# The remote lib: a bare repository whose one commit holds a minimal
# astra.yaml, cloned from a repository made beside it, which then goes.
lib=$ASTRA_CASE_REMOTES/lib
git init --quiet "$lib.work"
cat > "$lib.work/astra.yaml" <<'EOF'
spec_version: "0.1.0"
outputs:
  result:
    type: metric
    format: json
    recipe:
      command: python make.py '{output}'
EOF
git -C "$lib.work" add astra.yaml
git -C "$lib.work" commit --quiet --message lib
git clone --quiet --bare "$lib.work" "$lib"
rm -rf "$lib.work"

# The analysis's repository, with lib added as a submodule. Once it is
# committed, lib's checkout is removed, which leaves lib an empty folder.
git init --quiet
git submodule add --quiet "file://$lib" lib
git add --all
git commit --quiet --message files
git submodule deinit --quiet --force lib
