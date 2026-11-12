# stage is a symlink to the folder real_stage. One commit holds every file
# and the symlink.
ln -s real_stage stage
git init --quiet
git add --all
git commit --quiet --message files
