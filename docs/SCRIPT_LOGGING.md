# Script Logging - pre_stop and post_start Output

## Overview

The `pre_stop` and `post_start` scripts now have **enhanced logging** that shows their output in:
- ✅ Docker logs (`docker logs docker-compose-playground`)
- ✅ Web UI logs (`venv/web.log`)
- ✅ Console output when running `start-webui.sh` directly

All script output is logged at **INFO** level, making it visible by default.

## What You'll See

### When a script starts:
```
================================================================================
SCRIPT EXECUTION START
  Container: playground-mysql-8
  Type: init (post_start)
  Scripts to execute: 2
    1. default (mysql-8/playground-mysql-8-init.sh)
    2. custom (inline)
================================================================================
```

### Script output:
```
>> Executing init script: playground-mysql-8-init.sh (attempt 1/3, timeout: 300s)
✓ init script succeeded (exit code: 0, elapsed: 2.34s)
============================================================
INIT SCRIPT OUTPUT:
============================================================
  Waiting for MySQL to be ready...
  MySQL is ready!
  Creating database 'myapp'...
  Database created successfully
  Importing schema...
  Schema imported
============================================================
```

### When all scripts complete:
```
================================================================================
SCRIPT EXECUTION COMPLETED - All scripts succeeded
  Container: playground-mysql-8
  Type: init
  Total scripts executed: 2
================================================================================
```

## Configuration

You can control script logging behavior via environment variables in your `.env` file:

```bash
# Enable/disable script output logging (default: true)
PLAYGROUND_SCRIPT_OUTPUT_LOGGING=true

# Maximum number of output lines to log per script (default: 100)
PLAYGROUND_SCRIPT_MAX_OUTPUT_LINES=100

# Script execution timeouts in seconds (default: 300)
PLAYGROUND_SCRIPT_TIMEOUT=300
PLAYGROUND_SCRIPT_INIT_TIMEOUT=300   # post_start scripts
PLAYGROUND_SCRIPT_HALT_TIMEOUT=300   # pre_stop scripts
```

## Viewing Logs

### Docker Logs (Real-time)
```bash
# Follow logs
docker logs -f docker-compose-playground

# Last 100 lines
docker logs --tail 100 docker-compose-playground
```

### Web UI Log File
```bash
# Follow the log file
tail -f venv/web.log

# Search for script execution
grep "SCRIPT EXECUTION" venv/web.log
```

### Using start-webui.sh
```bash
# With live tail
./start-webui.sh --tail

# Normal mode (shows logs in console)
./start-webui.sh
```

## Example Output in Docker Logs

When you start or stop a container with scripts:

```bash
$ docker logs -f docker-compose-playground

[2025-11-01 10:15:23] [INFO    ] [scripts] ================================================================================
[2025-11-01 10:15:23] [INFO    ] [scripts] SCRIPT EXECUTION START
[2025-11-01 10:15:23] [INFO    ] [scripts]   Container: playground-mysql-8
[2025-11-01 10:15:23] [INFO    ] [scripts]   Type: init (post_start)
[2025-11-01 10:15:23] [INFO    ] [scripts]   Scripts to execute: 1
[2025-11-01 10:15:23] [INFO    ] [scripts]     1. default (mysql-8/playground-mysql-8-init.sh)
[2025-11-01 10:15:23] [INFO    ] [scripts] ================================================================================
[2025-11-01 10:15:23] [INFO    ] [scripts] >> Executing init script: playground-mysql-8-init.sh (attempt 1/3, timeout: 300s)
[2025-11-01 10:15:25] [INFO    ] [scripts] ✓ init script succeeded (exit code: 0, elapsed: 2.15s)
[2025-11-01 10:15:25] [INFO    ] [scripts] ============================================================
[2025-11-01 10:15:25] [INFO    ] [scripts] INIT SCRIPT OUTPUT:
[2025-11-01 10:15:25] [INFO    ] [scripts] ============================================================
[2025-11-01 10:15:25] [INFO    ] [scripts]   MySQL initialization started
[2025-11-01 10:15:25] [INFO    ] [scripts]   Database created: myapp
[2025-11-01 10:15:25] [INFO    ] [scripts]   User created: myapp_user
[2025-11-01 10:15:25] [INFO    ] [scripts]   Permissions granted
[2025-11-01 10:15:25] [INFO    ] [scripts] ============================================================
[2025-11-01 10:15:25] [INFO    ] [scripts] ================================================================================
[2025-11-01 10:15:25] [INFO    ] [scripts] SCRIPT EXECUTION COMPLETED - All scripts succeeded
[2025-11-01 10:15:25] [INFO    ] [scripts]   Container: playground-mysql-8
[2025-11-01 10:15:25] [INFO    ] [scripts]   Type: init
[2025-11-01 10:15:25] [INFO    ] [scripts]   Total scripts executed: 1
[2025-11-01 10:15:25] [INFO    ] [scripts] ================================================================================
```

## Features

✅ **Colored output** in console (when using start-webui.sh)
✅ **Automatic retry** on script failure (configurable, max 2 retries)
✅ **Timeout protection** (5 minutes default per script)
✅ **Line-by-line output** for better readability
✅ **Both stdout and stderr** are captured and logged
✅ **Error highlighting** (stderr shown in red/ERROR level)
✅ **Execution timing** (shows how long each script took)

## Troubleshooting

### Script output not showing?

1. Check if output logging is enabled:
   ```bash
   # In .env file
   PLAYGROUND_SCRIPT_OUTPUT_LOGGING=true
   ```

2. Verify log level (should be INFO or DEBUG):
   ```bash
   # Check container environment
   docker exec docker-compose-playground env | grep LOG
   ```

3. Check if script produces output:
   ```bash
   # Scripts should write to stdout
   echo "My output message"

   # Not to stderr (unless it's an error)
   ```

### Too much output?

Limit the number of lines logged:
```bash
# In .env file
PLAYGROUND_SCRIPT_MAX_OUTPUT_LINES=50
```

Or disable script output logging entirely:
```bash
# In .env file
PLAYGROUND_SCRIPT_OUTPUT_LOGGING=false
```

## Related Files

- **Script execution**: `src/web/core/scripts.py`
- **Docker integration**: `src/web/core/docker.py`
- **Logging config**: `src/web/core/logging_config.py`
- **Environment**: `docker-compose-standalone.yml`
