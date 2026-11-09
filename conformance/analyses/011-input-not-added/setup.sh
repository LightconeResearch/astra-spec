# The commit holds astra.yaml alone. The input's file stays in the working
# tree, untracked.
git init --quiet
git add astra.yaml
git commit --quiet --message files
