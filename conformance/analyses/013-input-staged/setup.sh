# The commit holds astra.yaml alone. data/input1.csv is then added to the
# index, and is in no commit.
git init --quiet
git add astra.yaml
git commit --quiet --message files
git add data/input1.csv
