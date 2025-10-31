# Docker Compose Parameter Support

## Overview

The playground configuration files now support standard Docker Compose parameters. This allows you to use familiar Docker Compose options like `extra_hosts`, `mem_limit`, `cpu_shares`, and many more directly in your YAML configuration files.

## Features

✅ **50+ Docker Compose parameters** supported
✅ **Automatic validation** of parameter names and types
✅ **Works with all interfaces** (CLI, Web UI, TUI)
✅ **Backward compatible** with existing configurations
✅ **Helpful warnings** for unknown parameters

## Supported Parameters

### Network & Connectivity
- `extra_hosts` (dict) - Add hostname mappings
- `dns` (list) - Custom DNS servers
- `dns_search` (list) - Custom DNS search domains
- `mac_address` (str) - Container MAC address
- `hostname` (str) - Container host name

### Security
- `cap_add` (list) - Add Linux capabilities
- `cap_drop` (list) - Drop Linux capabilities
- `privileged` (bool) - Give extended privileges
- `security_opt` (list) - Security options (seccomp, apparmor)
- `user` (str) - Username or UID

### Resources
- `mem_limit` (str/int) - Memory limit (e.g., '512m', '2g')
- `memswap_limit` (str/int) - Swap limit
- `shm_size` (str/int) - Size of /dev/shm
- `cpu_shares` (int) - CPU shares (relative weight)
- `cpuset_cpus` (str) - CPUs to use (e.g., '0-3', '0,1')
- `cpu_quota` (int) - CPU CFS quota
- `cpu_period` (int) - CPU CFS period
- `pids_limit` (int) - Container pids limit

### Process Management
- `oom_kill_disable` (bool) - Disable OOM Killer
- `oom_score_adj` (int) - OOM preferences (-1000 to 1000)
- `pid_mode` (str) - PID namespace (e.g., 'host')
- `ipc_mode` (str) - IPC mode (e.g., 'host', 'shareable')
- `init` (bool) - Run init inside container

### Storage
- `tmpfs` (dict) - Mount tmpfs directories
- `devices` (list) - Device mappings
- `device_read_bps` (list) - Limit read rate from device
- `device_write_bps` (list) - Limit write rate to device
- `device_read_iops` (list) - Limit read IOPS from device
- `device_write_iops` (list) - Limit write IOPS to device
- `read_only` (bool) - Mount root filesystem as read-only
- `storage_opt` (dict) - Storage driver options

### System
- `sysctls` (dict) - Kernel parameters
- `ulimits` (list) - Ulimit options
- `working_dir` (str) - Working directory
- `runtime` (str) - Runtime to use (e.g., 'nvidia')

### Health & Monitoring
- `healthcheck` (dict) - Healthcheck configuration

### Restart Policy
- `restart_policy` (dict) - Restart policy configuration

### Logging
- `log_config` (dict) - Logging configuration

### Groups & Namespaces
- `group_add` (list) - Additional groups
- `userns_mode` (str) - User namespace

### Network Mode
- `network_mode` (str) - Network mode (bridge/host/none)

## Usage Examples

### Example 1: Extra Hosts

Add custom hostname mappings to `/etc/hosts`:

```yaml
images:
  my-app:
    image: "alpine:latest"
    category: "linux"
    keep_alive_cmd: "sleep infinity"
    shell: "/bin/sh"

    # Map hostnames to IP addresses
    extra_hosts:
      api.example.com: "192.168.1.100"
      db.example.com: "192.168.1.200"
      cache.example.com: "192.168.1.150"
```

**Verification:**
```bash
./playground start my-app
./playground exec my-app "cat /etc/hosts"
```

### Example 2: Custom DNS

Configure custom DNS servers and search domains:

```yaml
images:
  dns-test:
    image: "alpine:latest"
    category: "linux"
    keep_alive_cmd: "sleep infinity"
    shell: "/bin/sh"

    # Custom DNS configuration
    dns:
      - "8.8.8.8"
      - "8.8.4.4"

    dns_search:
      - "example.com"
      - "internal.local"
```

### Example 3: Resource Limits

Set memory and CPU limits:

```yaml
images:
  resource-limited:
    image: "alpine:latest"
    category: "linux"
    keep_alive_cmd: "sleep infinity"
    shell: "/bin/sh"

    # Resource constraints
    mem_limit: "512m"
    memswap_limit: "1g"
    cpu_shares: 512
    cpuset_cpus: "0-1"
    pids_limit: 100
```

### Example 4: Security & Capabilities

Run with elevated privileges:

```yaml
images:
  privileged-app:
    image: "alpine:latest"
    category: "linux"
    keep_alive_cmd: "sleep infinity"
    shell: "/bin/sh"

    # Security settings
    privileged: true  # Use with caution!

    cap_add:
      - NET_ADMIN
      - SYS_TIME

    cap_drop:
      - MKNOD
```

### Example 5: Shared Memory & Tmpfs

Configure shared memory and tmpfs mounts:

```yaml
images:
  shm-test:
    image: "alpine:latest"
    category: "linux"
    keep_alive_cmd: "sleep infinity"
    shell: "/bin/sh"

    # Increase shared memory
    shm_size: "256m"

    # Mount tmpfs
    tmpfs:
      /tmp: "size=100m"
      /run: "rw,noexec,nosuid,size=64m"
```

### Example 6: Working Directory

Set default working directory:

```yaml
images:
  app-workdir:
    image: "node:18"
    category: "programming"
    keep_alive_cmd: "sleep infinity"
    shell: "/bin/bash"

    # Set working directory
    working_dir: "/app"
```

### Example 7: System Controls

Configure kernel parameters:

```yaml
images:
  sysctl-test:
    image: "alpine:latest"
    category: "linux"
    keep_alive_cmd: "sleep infinity"
    shell: "/bin/sh"

    # Kernel parameters
    sysctls:
      net.ipv4.ip_forward: "1"
      net.core.somaxconn: "1024"
```

## Validation

The playground automatically validates Docker Compose parameters:

### ✅ Valid Parameter (Silent)
```yaml
images:
  test:
    image: "alpine:latest"
    keep_alive_cmd: "sleep infinity"
    extra_hosts:
      api.local: "10.0.0.1"
```

### ⚠️ Unknown Parameter (Warning)
```yaml
images:
  test:
    image: "alpine:latest"
    keep_alive_cmd: "sleep infinity"
    unknown_param: "value"  # Warning: Unknown parameter
```

### ❌ Invalid Type (Error)
```yaml
images:
  test:
    image: "alpine:latest"
    keep_alive_cmd: "sleep infinity"
    extra_hosts: "not-a-dict"  # Error: extra_hosts expects dict
```

## How It Works

1. **Configuration Loading**: When you add Docker Compose parameters to your YAML files, they're loaded along with playground-specific parameters.

2. **Validation**: Parameters are validated against the Docker Compose specification:
   - Parameter names are checked against the supported list
   - Parameter values are type-checked (dict, list, str, bool, int)

3. **Extraction**: Valid Docker Compose parameters are extracted and separated from playground-specific parameters.

4. **Application**: The parameters are passed directly to the Docker SDK's `containers.run()` method.

## Reserved Parameters

Some parameters are handled by playground and should not be specified in your config:

- `image` - Handled by playground
- `container_name` / `name` - Auto-generated
- `ports` - Use playground's `ports` format
- `volumes` - Use playground's `volumes` format
- `environment` - Use playground's `environment` format
- `command` - Use `keep_alive_cmd` instead
- `labels` - Partially handled (playground.managed label)
- `networks` / `network` - Auto-connected to playground-network
- `detach` / `stdin_open` / `tty` - Always enabled

## Testing

Test configurations are provided in `custom.d/test-docker-compose-params.yml`:

```bash
# List test containers
./playground list | grep test-

# Test extra_hosts
./playground start test-extra-hosts
./playground exec test-extra-hosts "cat /etc/hosts"
./playground stop test-extra-hosts

# Test privileged mode
./playground start test-privileged
./playground exec test-privileged "cat /proc/self/status | grep Cap"
./playground stop test-privileged

# Test resource limits
./playground start test-resources
./playground exec test-resources "free -h"
./playground stop test-resources
```

## Troubleshooting

### Container fails to start with new parameters

1. Check the Docker logs:
   ```bash
   ./playground logs <container-name>
   ```

2. Verify parameter syntax in your YAML file

3. Test with minimal parameters first, then add more

### Warning: Unknown parameter

This is just a warning and won't prevent the container from starting. The parameter will be ignored. Check:
- Is the parameter name spelled correctly?
- Is it a standard Docker Compose parameter?
- See the "Supported Parameters" section above

### Type validation error

Ensure the parameter value matches the expected type:
- `dict`: Use key-value pairs with colons
- `list`: Use dash-prefixed items
- `str`: Use quoted text
- `bool`: Use `true` or `false`
- `int`: Use numbers without quotes

## Migrating from Docker Compose

If you have an existing `docker-compose.yml`, you can migrate parameters:

**Docker Compose:**
```yaml
services:
  myapp:
    image: alpine:latest
    extra_hosts:
      - "api.local:10.0.0.1"
      - "db.local:10.0.0.2"
    mem_limit: 512m
    dns:
      - 8.8.8.8
```

**Playground Config:**
```yaml
images:
  myapp:
    image: "alpine:latest"
    keep_alive_cmd: "sleep infinity"
    shell: "/bin/sh"
    category: "linux"

    extra_hosts:
      api.local: "10.0.0.1"
      db.local: "10.0.0.2"

    mem_limit: "512m"

    dns:
      - "8.8.8.8"
```

**Key Differences:**
1. `extra_hosts` uses dict format instead of list
2. Add playground-specific fields: `keep_alive_cmd`, `shell`, `category`
3. Wrap strings in quotes for YAML safety

## API Reference

For developers integrating with playground:

### Python Module: `docker_compose_params.py`

```python
from src.cli.core.docker_compose_params import (
    validate_docker_compose_key,
    validate_parameter_value,
    extract_docker_params,
    validate_all_params,
    get_supported_params,
    get_param_type
)

# Validate a single key
is_valid, message = validate_docker_compose_key("extra_hosts")

# Extract Docker params from config
docker_params = extract_docker_params(img_data)

# Validate all parameters
is_valid, errors, warnings = validate_all_params(img_data, strict=False)

# Get all supported parameters
params = get_supported_params()
```

## Contributing

To add support for new Docker Compose parameters:

1. Edit `src/cli/core/docker_compose_params.py` and `src/web/core/docker_compose_params.py`
2. Add parameter to `DOCKER_COMPOSE_PARAMS` dict:
   ```python
   "param_name": ("sdk_key_name", expected_type, "Description"),
   ```
3. Test with a sample configuration
4. Update this documentation

## References

- [Docker Compose File Reference](https://docs.docker.com/compose/compose-file/)
- [Docker SDK for Python](https://docker-py.readthedocs.io/)
- [Docker Engine API](https://docs.docker.com/engine/api/)

---

**Need Help?**
Open an issue on GitHub or check the example configurations in `custom.d/test-docker-compose-params.yml`
