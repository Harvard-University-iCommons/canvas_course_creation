#!/bin/bash
export HOME=/home/vagrant
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh
mkvirtualenv -a /home/vagrant/canvas_course_creation -r /home/vagrant/canvas_course_creation/canvas_course_creation/requirements/local.txt canvas_course_creation
