# The first commit, C1, holds stage/astra.yaml, which reads
# stage/data/input1.csv, but not the file.
git init --quiet
git add stage/astra.yaml
git commit --quiet --message C1
git tag C1

# The second holds the rest, with astra.yaml declaring stage at C1.
commit=$(git rev-parse C1)
sed "s/@commit:C1@/$commit/" astra.yaml > astra.yaml.new
mv astra.yaml.new astra.yaml
git add --all
git commit --quiet --message files
