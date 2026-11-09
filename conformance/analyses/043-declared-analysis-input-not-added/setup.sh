# Every file is committed but stage/data/input2.csv, which stays in the
# working tree, untracked.
git init --quiet
git add astra.yaml stage/astra.yaml
git commit --quiet --message files
