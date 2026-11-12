# The first commit, C1, holds an earlier astra.yaml: decision1, output1 and
# the universe u1.
git init --quiet
mv astra.yaml astra.yaml.final
cat > astra.yaml <<'EOF'
spec_version: "0.1.0"
decisions:
  decision1:
    options:
      a: {}
      b: {}
outputs:
  output1:
    type: metric
    format: json
    decisions: [decision1]
    recipe:
      command: python make.py '{decisions.decision1}' '{output}'
universes:
  u1:
    decisions: {decision1: a}
EOF
git add astra.yaml
git commit --quiet --message C1
git tag C1

# The second holds the final astra.yaml, which declares the analysis's own
# folder at C1 as previous.
commit=$(git rev-parse C1)
sed "s/@commit:C1@/$commit/" astra.yaml.final > astra.yaml
rm astra.yaml.final
git add --all
git commit --quiet --message files
