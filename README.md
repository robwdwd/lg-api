# Looking Glass

Python Network Looking Glass API backend

---

## Installation

1. **Download**  
   Download the source or release file and place it anywhere on your filesystem.

2. **Create a Virtual Environment**  
   [Poetry](https://python-poetry.org/docs/#installation) is recommended, but any venv tool will work.  
   Install dependencies:

   ```console
   poetry install --nodev
   ```

---

## Configuration

Copy `examples/env.example` to `.env` in the project root (not the package folder).

### Environment Variables

| Variable                   | Description                                                                                  |
|----------------------------|----------------------------------------------------------------------------------------------|
| `PORT`                     | Port number the application listens on (default: 8012).                                      |
| `LISTEN`                   | IP/interface to bind the server (default: 127.0.0.1).                                        |
| `WORKERS`                  | Number of worker processes (default: 4).                                                     |
| `ROOT_PATH`                | Root path for the app (e.g., `/` or `/lg`).                                                  |
| `USERNAME`                 | Username for authentication.                                                                 |
| `PASSWORD`                 | Password for authentication.                                                                 |
| `ENVIRONMENT`              | Environment type (`prod` or `dev`).                                                          |
| `LOG_LEVEL`                | Logging level (`debug`, `info`, `warning`, `error`, etc).                                    |
| `LOG_DIR`                  | Directory for log files (default: `/var/log/lg/`).                                           |
| `CONFIG_FILE`              | Path to main config file (default: `config.yml`).                                            |
| `PING_MULTI_MAX_SOURCE`    | Max source locations for multi-ping (default: 3).                                            |
| `PING_MULTI_MAX_IP`        | Max IPs for multi-ping (default: 5).                                                         |
| `BGP_MULTI_MAX_SOURCE`     | Max source locations for multi-BGP (default: 3).                                             |
| `BGP_MULTI_MAX_IP`         | Max IPs for multi-BGP (default: 5).                                                          |
| `RESOLVE_TRACEROUTE_HOPS`  | Traceroute hop resolution: `off`, `missing`, or `all` (default: `off`).                      |
| `USE_REDIS_CACHE`           | Set to `True` to use Redis as a cache, or `False` for in-memory cache.                      |
| `REDIS_HOST`                | Redis server hostname or IP address (default: `127.0.0.1`).                                 |
| `REDIS_PORT`                | Redis server port (default: `6379`).                                                        |
| `REDIS_TIMEOUT`             | Redis connection timeout in seconds (default: `5`).                                         |
| `REDIS_PASSWORD`            | (Optional) Password for Redis server.                                                       |
| `REDIS_NAMESPACE`           | Namespace prefix for Redis keys (default: `lgapi`).                                         |

---

### Caching

The API caches results from external services such as the Cymru IP to ASN service, Caida AS rank API, and reverse DNS lookups to improve performance and reduce external requests.

By default, caching is done in memory.  

To use Redis for caching set `USE_REDIS_CACHE=True` in your `.env` file and customise the Redis connection variables if required.

### Location and Command Configuration

Copy `examples/config.yml.example` to `config.yml` in the root folder.  
Change the configuration file path using `CONFIG_FILE` in `.env` if needed.

- The config file lists locations, devices, and CLI commands for each device type.
- Supported device types: [scrapli device types](https://carlmontanari.github.io/scrapli/user_guide/basic_usage/)

**Example:**

```yaml
locations:
  AMS:                              # Location Code
    name: Amsterdam                 # Location name
    region: Western Europe          # Region
    device: router.ams.example.net  # Device hostname
    type: cisco_iosxr               # Any scrapli supported device type
    source: loopback999             # Source interface or IP address for ping and traceroute commands
```

**Commands:**

`IPADDRESS` is substituted for the destination IP address or prefix, and `SOURCE` is substituted for the source IP or interface (from the location's `source` key):

```yaml
commands:
  ping:
    cisco_iosxr:
      ipv4: ping IPADDRESS source SOURCE
      ipv6: ping IPADDRESS source SOURCE
    juniper_junos:
      ipv4: ping IPADDRESS source SOURCE count 5
      ipv6: ping IPADDRESS source SOURCE count 5
  bgp:
    cisco_iosxr:
      ipv4: show bgp ipv4 unicast IPADDRESS
      ipv6: show bgp ipv6 unicast IPADDRESS
    juniper_junos:
      ipv4: show route IPADDRESS protocol bgp detail
      ipv6: show route IPADDRESS protocol bgp detail
  traceroute:
    cisco_iosxr:
      ipv4: traceroute IPADDRESS source SOURCE timeout 2
      ipv6: traceroute IPADDRESS source SOURCE timeout 2
    juniper_junos:
      ipv4: traceroute IPADDRESS source SOURCE
      ipv6: traceroute IPADDRESS source SOURCE
```

---

## Traceroute Hop Resolution

Set `RESOLVE_TRACEROUTE_HOPS` in `.env`:

- `off`: Use router output only.
- `missing`: Resolve only unresolved hops.
- `all`: Resolve all hops, ignoring router resolution.

**Tip:**  
Disable reverse DNS lookup on the routers to speed up the traceroutes. Example config:

```yaml
traceroute:
    cisco_iosxr:
      ipv4: traceroute IPADDRESS numeric source SOURCE timeout 2
      ipv6: traceroute IPADDRESS numeric source SOURCE timeout 2
    juniper_junos:
      ipv4: traceroute IPADDRESS no-resolve source SOURCE
      ipv6: traceroute IPADDRESS no-resolve source SOURCE
```

---

## Community Maps

Community maps convert BGP community output to human-friendly text.  
Copy `examples/communities.txt` to the `mapsdb` folder.  
Restart the server after changes.

---

## Permissions

Set permissions for the `mapsdb` folder and `.env` file:

```console
chgrp <web_server_user> mapsdb .env
chmod g+s mapsdb
setfacl -dR -m u:<web_server_user>:rwX -m u:<your_user>:rwX mapsdb
```

---

## Running the Development Server

Use Poetry or another virtual environment:

```console
poetry shell
fastapi dev lgapi/main.py
```

---

## Systemd Service

1. Copy the example unit file:

   ```console
   cp examples/lgapi.service /etc/systemd/system/lgapi.service
   ```

2. Edit `WorkingDirectory`, `User`, `Group`, `PATH`, and `VIRTUAL_ENV` as needed.

3. Create the log directory and set permissions:

   ```console
   mkdir /var/log/lg/
   chown www-data.www-data /var/log/lg/
   ```

4. Enable and start the service:

   ```console
   systemctl daemon-reload
   systemctl enable lgapi.service
   systemctl start lgapi.service
   ```

---

## Nginx Configuration

A reverse proxy via Nginx is recommended.  
If serving under a subpath, set `ROOT_PATH` in `.env` (e.g., `ROOT_PATH=/lgapi`).

See [examples/nginx.conf](examples/nginx.conf) and [examples/nginx-subpath.conf](examples/nginx-subpath.conf) for sample configs.
