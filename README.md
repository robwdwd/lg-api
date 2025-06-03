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

The configuration file lists locations, devices, and CLI commands for each device type as well as the Looking glass API settings

Copy `examples/config.yml.example` to `config.yml` in the project root and edit as needed.  

### Configuration Options Reference

The `config.yml` file controls the main application settings. Below are the primary options you can configure:

| Option                        | Type      | Description                                                            | Example                          |
|-------------------------------|-----------|------------------------------------------------------------------------|----------------------------------|
| `authentication.groups`       | mapping   | Authentication groups with username/password for device access         | See below                        |
| `title`                       | string    | API title (displayed in docs and UI)                                   | `Looking Glass API`              |
| `resolve_traceroute_hops`     | string    | How to resolve traceroute hops: `off`, `all`, or `missing`             | `off`                            |
| `log_level`                   | string    | Logging level: `critical`, `error`, `warning`, `info`, `debug`, `trace`| `info`                           |
| `root_path`                   | string    | Root path for the API (useful if served under a subpath)               | `/` or `/lgapi`                  |
| `environment`                 | string    | Environment: `prod` or `devel`                                         | `prod`                           |
| `limits.max_sources.bgp`      | integer   | Max source locations for BGP queries                                   | `3`                              |
| `limits.max_sources.ping`     | integer   | Max source locations for ping queries                                  | `3`                              |
| `limits.max_destinations.bgp` | integer   | Max destination addresses for BGP queries                              | `3`                              |
| `limits.max_destinations.ping`| integer   | Max destination addresses for ping queries                             | `3`                              |
| `cache.redis.enabled`         | boolean   | Enable Redis caching                                                   | `true` or `false`                |
| `cache.redis.dsn`             | string    | Redis DSN connection string                                            | `redis://localhost:6379/0`       |
| `cache.redis.namespace`       | string    | Namespace for Redis keys                                               | `lgapi`                          |
| `cache.redis.timeout`         | integer   | Redis connection timeout (seconds)                                     | `5`                              |
| `locations`                   | mapping   | List of locations/devices (see below for structure)                    |                                  |
| `commands`                    | mapping   | CLI command templates for each device type (see below for structure)   |                                  |

### Device Authentication

Device authentication is managed via the `authentication.groups` section in your `config.yml`.  
You can define multiple authentication groups, each with its own username and password.  
Each device (location) can specify which group to use via the `authentication` key.  
If a device does not specify a group, or specifies a non-existent group, the `fallback` group will be used.

```yaml
authentication:
  groups:
    core:
      username: myuser
      password: mypass
    access:
      username: otheruser
      password: otherpass
    fallback:
      username: fallbackuser
      password: fallbackpass
```

- The `fallback` group **must** exist.
- Assign a group to a device using the `authentication` key under each location.
- If omitted, the `fallback` group credentials are used.

### Locations

- Supported device types: [scrapli device types](https://carlmontanari.github.io/scrapli/user_guide/basic_usage/)

**Example:**

```yaml
locations:
  AMS:                              # Location Code
    name: Amsterdam                 # Location name
    region: Western Europe          # Region
    device: router.ams.example.net  # Device hostname
    authentication: core            # Use core authentication group, optional - will use fallback otherwise
    type: cisco_iosxr               # Any scrapli supported device type
    source: loopback999             # Source interface or IP address for ping and traceroute commands
  LON:                              # Juniper devices with no authentication line, fallback auth group will be used                  
    name: London                    
    region: Western Europe         
    device: router.lon.example.net  
    type: juniper_junos
    source: 192.168.0.1
```

### Commands

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

### Traceroute Hop Resolution

Set `resolve_traceroute_hops` in `config.yml`:

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

### Caching

The API caches results from external services such as the Cymru IP to ASN service, Caida AS rank API, and reverse DNS lookups to improve performance and reduce external requests.

By default, caching is done in memory.

**To use Redis for caching,** set the following in your `config.yml` file:

```yaml
cache:
  redis:
    enabled: true
    dsn: redis://localhost:6379/
    namespace: lgapi
    timeout: 5
```

You can customise the Redis connection variables as needed in `config.yml`.  

#### Redis DSN

The `dsn` field under `cache.redis` uses a **Redis DSN** (Data Source Name) to specify how to connect to your Redis server.  
The general format is:

```
redis://[:password]@host:port/db
```

**Examples:**

- Connect to Redis on localhost, default port, default database:

  ```
  redis://localhost:6379
  ```

- Connect to Redis with a password:

  ```
  redis://:mypassword@localhost:6379
  ```

- Connect to a remote Redis server, database 2:

  ```
  redis://redis.example.com:6379/2
  ```

- Connect to Redis with a password and custom port:

  ```
  redis://:secretpass@redis.example.com:6380/1
  ```

**Parts:**

- `redis://` — protocol
- `:password@` — optional password (leave out if not needed)
- `host` — Redis server hostname or IP
- `:port` — Redis port (default is 6379)
- `/db` — Redis database number (default is 0)

Use this DSN string in your `config.yml` under `cache.redis.dsn`.

---

## Environment Variables

Environment variables are used by Gunicorn for production use, they are not used by the looking glass API itself.

Copy `examples/env.example` to `.env` in the project root (not the package folder).

| Variable                   | Description                                                                                  |
|----------------------------|----------------------------------------------------------------------------------------------|
| `PORT`                     | Port number the application listens on (default: 8012).                                      |
| `LISTEN`                   | IP/interface to bind the server (default: 127.0.0.1).                                        |
| `WORKERS`                  | Number of worker processes (default: 4).                                                     |
| `ROOT_PATH`                | Root path for the app (e.g., `/` or `/lg`).                                                  |
| `LOG_DIR`                  | Directory for log files (default: `/var/log/lg/`).                                           |

---

## Community Maps

Community maps convert BGP community values into human-friendly text descriptions.

The `mapsdb/asns` folder contains the **default** community mapping files, with one `.txt` file per ASN (for example, `8220.txt`, `3356.txt`, etc.).  
**These files are part of the code base and should not be modified directly.** If you wish to contribute new ASN mappings, please submit a pull request.

To customise or override any mappings for your deployment, add files (ending in `.txt` and preferably named `<asn>.txt`) to the `mapsdb/override` folder.  
Mappings in the `override` folder will take precedence over those in the `asns` folder for the same community values, allowing you to tailor or supplement the default mappings without changing the code base.

**How it works:**

- When the application starts, it loads all mapping files from `mapsdb/asns` and then applies any overrides from `mapsdb/override`.
- If a community value exists in both, the override version is used.

**To update mappings:**

1. Add or edit a `.txt` file in `mapsdb/override` with your custom mappings.
2. Restart the server to apply the changes.

**Note:**  
Do **not** edit files in `mapsdb/asns` directly, as these may be overwritten during upgrades or by version control.

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
