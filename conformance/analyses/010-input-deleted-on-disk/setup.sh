# The one commit holds astra.yaml and data/input1.csv, which the script
# writes. Then data/input1.csv is deleted from the working tree, and git's
# index still lists it.
mkdir data
printf 'sample,value\n1,0.5\n' > data/input1.csv
git init --quiet
git add --all
git commit --quiet --message files
rm data/input1.csv
