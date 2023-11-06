#!/bin/bash

#
# Creating vector_search git repo
#
git init
git add .
git commit -m "Initial commit"
# git remote add origin git@github.com:thinknimble/vector_search.git
gh repo create thinknimble/vector_search --private -y
git push origin main
printf "\033[0;32mRepo https://github.com/thinknimble/vector_search/\033[0m \n"
