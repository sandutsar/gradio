#!/bin/bash
if [ -z "$(ls | grep CONTRIBUTING.md)" ]; then
  echo "Please run the script from repo directory"
  exit -1
else
  echo "Uploading to pypi"
  set -e
  git pull origin master
  old_version=$(grep -Po "(?<=version=\")[^\"]+(?=\")" setup.py)
  echo "Current version is $old_version. New version?"
  read new_version
  sed -i "s/version=\"$old_version\"/version=\"$new_version\"/g" setup.py
  read -p "frontend updates? " -r
  if [[ $REPLY =~ ^[Yy]$ ]]
  then
    echo -n $new_version > gradio/version.txt
    rm -rf gradio/templates/frontend
    cd ui
    pnpm i
    pnpm build
    cd ..
    aws s3 cp gradio/templates/frontend s3://gradio/$new_version/ --recursive  # requires aws cli (contact maintainers for credentials)
  fi
  rm -r dist/*
  rm -r build/*
  python3 setup.py sdist bdist_wheel
  python3 -m twine upload dist/*
  git add -A
  git commit -m "updated PyPi version to $new_version"
fi

