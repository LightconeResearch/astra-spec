# The remote lib: a bare repository whose one commit holds input1.csv,
# cloned from a repository made beside it, which then goes.
lib=$ASTRA_CASE_REMOTES/lib
git init --quiet "$lib.work"
printf 'sample,value\n1,0.5\n' > "$lib.work/input1.csv"
git -C "$lib.work" add input1.csv
git -C "$lib.work" commit --quiet --message lib
git clone --quiet --bare "$lib.work" "$lib"
rm -rf "$lib.work"

# The analysis's repository, with lib added as a submodule.
git init --quiet
git submodule add --quiet "file://$lib" lib
git add --all
git commit --quiet --message files
