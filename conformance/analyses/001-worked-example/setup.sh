# The remote upstream is a bare repository with one commit, U, which holds
# upstream's astra.yaml: an output, output4, built once.
upstream=$ASTRA_CASE_REMOTES/upstream
mkdir "$upstream.work"
cat > "$upstream.work/astra.yaml" <<'EOF'
spec_version: "0.1.0"
outputs:
  output4:
    type: metric
    format: json
    recipe:
      command: python src/output4.py '{output}'
EOF
git -C "$upstream.work" init --quiet
git -C "$upstream.work" add astra.yaml
git -C "$upstream.work" commit --quiet --message U
git -C "$upstream.work" tag U
git clone --quiet --bare "$upstream.work" "$upstream"
rm -rf "$upstream.work"

# One commit holds every file, with astra.yaml declaring upstream by its
# URL and U.
commit=$(git -C "$upstream" rev-parse U)
sed -e "s|@url:upstream@|file://$upstream|" -e "s|@commit:U@|$commit|" \
  astra.yaml > astra.yaml.new
mv astra.yaml.new astra.yaml
git init --quiet
git add --all
git commit --quiet --message files
