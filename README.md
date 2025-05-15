# Looking Glass

Python Network Looking Glass, API backend

## Install

Download either source or release file and put somewhere on your filesystem.

### Build Virtual environment

Poetry is used to build the virtual environment although
any other venv tools can be used to build it. Pipx is a good way to [install
poetry](https://python-poetry.org/docs/#installing-with-pipx) although you
can use any of the install methods listed
[here](https://python-poetry.org/docs/#installation)

```console
poetry install --nodev
```

### Configuration

Copy the [examples/env.example](examples/env.example) to `.env` in lg
root folder (not in the package folder.)

Make sure to change the `SECRET_KEY` and `CSRF_SECRET` in the `.env` file
and also set `DEBUG=False` for a production environment.

### Location and command configuration

Copy the [examples/config.yml.example](examples/config.yml.example) to config.yml in
the lg root folder (not in the package folder.) The path to this file can be changed
by changing CONFIG_FILE in the .env file.

The config file contains the list of cities, devices and cli commands
to run on each device type.

Any device type supported by scrapli is supported by the looking glass.
To find all the device types look
[here](https://carlmontanari.github.io/scrapli/user_guide/basic_usage/)

Every location needs a device (hostname), the device type, the full name of the
location, a region and a source interface or ip address (for traceroute and
ping commands).

```console
locations:
  AMS:
    name: Amsterdam
    region: Western Europe
    device: router.ams.example.net
    type: cisco_iosxr
    source: loopback999
```

The config.yml file also contains the commands to run on each device type.
In each command the string IPADDRESS is substituted for the IP Address or CIDR
the user enters on the form and SOURCE is substiuted for the source in the location
configuration. IOS-XR and JunOS commands are in the example but you can add more
support for other devices provided netmiko supports that device type.

### Community maps

Community maps convert the community output in the bgp command to be more human
friendly. Copy [examples/communities.txt](examples/communities.txt) to the mapsdb folder.
This is then read at start up and saved to a sqlite database for access. Making any
changes to the communities.txt file requires a server restart.

### Change permissions

Change the group permissions of the mapsdb folder to the group of your web server
and add group sticky bit. Make the .env file readable to the web server.

```console
chgrp www-data mapsdb .env
chmod g+s mapsdb
```

## Running development server

Run the helper app directly. Use poetry or another virtual environment.

```console
poetry shell
fastapi dev lgapi/main.py
```

## Systemd service

Create a systemd unit file to start the lg service at startup.
An example unit file [examples/lgapi.service](examples//lgapi.service)
can be used and edited as needed.

```console
cp examples/lgapi.service /etc/systemd/system/lgapi.service
```

Edit the file and change the following as needed `WorkingDirectory`,
`User`, `Group`. Also alter `PATH` and `VIRTUAL_ENV`
Environment variables to match your install location.

Make the log directory used by the service (gunicorn logs). Set `LOG_DIR` in
the `.env` file to change this if required and change the username to the
same user and group as in the unit file.

```console
mkdir /var/log/lg/
chown www-data.www-data /var/log/lg/
```

By default it runs on port 8010 and listens only on localhost. Change
this in the `.env` file.

Finally enable the service

```console
systemctl daemon-reload
systemctl enable lgapi.service
systemctl start lgapi.service
```

## Nginx configuration

A reverse proxy via Nginix is optional but recommeded step. If the pages are
served under a sub path modify the `ROOT_PATH` in `.env`
to match for example `ROOT_PATH=/lg`

See [examples/nginx.conf](examples/nginx.conf) and
[examples/nginx-subpath.conf](examples/nginx-subpath.conf) configuration for
a base to get started.
