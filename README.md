# samba4_manager
User manager for Samba, which uses Samba Python bindings. Allows to perform all the operations of user and group management.

## Description

This tool is a web application that will provide user management for Samba. It interacts with Samba directly through its Python bindings. 

It will allow for creation, modification and deletion of users and groups, with the ultimate goal to replicate the functions of the "Active Directory Users and Groups".

Both Python 2.7 and 3.6 are supported for this application.

## Motivation

The GUI tools available for Linux are general-purpose configuration editors such as Webmin, which don't satisfactorily handle Samba4 user management, and don't allow for the extensive modification of properties allowed by the Windows-based tool "Active Directory Users and Groups". That tool can be used from Windows to connect and manage a Samba4 domain, but there is no equivalent tool for Linux.

The use of Python for the creation of this tool is to make use of the Python bindings for Samba4, which make direct use of internal Samba data structures. And it can be a good excuse to learn the Python language in the process ;-). 

## Installation

### Pre-requisites

The following packages have to be installed:

sudo yum install samba python3-samba python3-samba-devel samba-dc-libs python3-samba-dc

The following python packages need to be installed:

pip install mod_wsgi

To find the required configuration that is needed for Apache to be configured to load mod_wsgi as a module, run this:

/usr/local/bin/mod_wsgi-express module-config

### Package installation with pip

For now, the process to release the application as a Python package nas not been completed. To deploy this application, the following steps need to be performed:

1. git clone of this repository into a folder available to the web server.
2. pip install -e .
3. Configure to launch from either the web server or the standalone tool "pserve"

### As a HTTP module

This example configuration applies to the Apache web server: 

```
# Use only 1 Python sub-interpreter.  Multiple sub-interpreters
# play badly with C extensions.  See
# http://stackoverflow.com/a/10558360/209039
WSGIApplicationGroup %{GLOBAL}
WSGIPassAuthorization On
WSGIDaemonProcess pyramid user=unbound group=unbound threads=4 \
   python-path=/opt/rh/rh-python36/root/usr/bin/python
WSGIScriptAlias /samba4_manager /var/www/html/samba4_manager/pyramid.wsgi

<Directory /var/www/html/samba4_manager>
  WSGIProcessGroup pyramid
  Require all granted
</Directory>
```

Python 3.6 is not necessarily required, the application can run just as well using Python 2.7. 

### As a standalone application

You can run the application from the command-line using the command below. It will launch a web server process that will listen on port 6543:

```
/usr/bin/pserve development.ini --reload
```
