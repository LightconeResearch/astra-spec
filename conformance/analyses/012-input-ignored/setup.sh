# .gitignore ignores data/, so the one commit leaves data/input1.csv out:
# the file stays on disk, ignored.
printf 'data/\n' > .gitignore
git init --quiet
git add --all
git commit --quiet --message files
