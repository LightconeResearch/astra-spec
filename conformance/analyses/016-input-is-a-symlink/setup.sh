# data/input1.csv is a symlink to raw/input1.csv, an ordinary file, and
# the one commit holds it as a symlink.
mkdir data
ln -s ../raw/input1.csv data/input1.csv
git init --quiet
git add --all
git commit --quiet --message files
