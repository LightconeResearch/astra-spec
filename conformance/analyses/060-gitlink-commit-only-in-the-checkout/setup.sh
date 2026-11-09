# The remote lib: a bare repository whose one commit holds a README, cloned
# from a repository made beside it, which then goes.
lib=$ASTRA_CASE_REMOTES/lib
git init --quiet "$lib.work"
echo "A library." > "$lib.work/README"
git -C "$lib.work" add README
git -C "$lib.work" commit --quiet --message README
git clone --quiet --bare "$lib.work" "$lib"
rm -rf "$lib.work"

# The first commit adds the remote as the submodule lib.
git init --quiet
git submodule add --quiet "file://$lib" lib
git commit --quiet --message submodule

# In the submodule's checkout, the commit P adds an analysis. It isn't
# pushed, so the remote doesn't have it.
cat > lib/astra.yaml <<'EOF'
spec_version: "0.1.0"
outputs:
  result:
    type: metric
    format: json
    recipe:
      command: python make.py '{output}'
EOF
git -C lib add astra.yaml
git -C lib commit --quiet --message P

# The commit C pins lib at P.
git add lib
git commit --quiet --message C
git tag C

# The checkout moves on to Q, which removes the analysis. So lib's working
# tree holds no astra.yaml, and only P, which the gitlink at C pins, holds
# one.
git -C lib rm --quiet astra.yaml
git -C lib commit --quiet --message Q

# The last commit pins lib at Q and holds astra.yaml, which declares lib
# at C.
commit=$(git rev-parse C)
sed "s/@commit:C@/$commit/" astra.yaml > astra.yaml.new
mv astra.yaml.new astra.yaml
git add --all
git commit --quiet --message files
