from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import select
import asyncio
from typing import Optional
import asyncio
import logging
from src.web.core.logging_config import get_logger
import docker
import json
import time

from src.web.core.config import load_config, get_motd
from src.web.core.docker import docker_client
from src.web.utils.motd_processor import format_motd_for_terminal
from src.web.utils import to_full_name, to_display_name

router = APIRouter()
logger = get_logger(__name__)

# Track active WebSocket sessions
active_sessions: dict = {}
active_sessions_lock = asyncio.Lock()

class WebSocketConfig:
    """WebSocket performance configuration"""

    # Buffer sizes (increased for better throughput)
    SOCKET_RECV_BUFFER = 16384  # 16KB - larger buffer for faster reads
    SOCKET_SEND_BUFFER = 16384  # 16KB - larger buffer for faster writes

    # Polling optimization
    # Reduced timeout for more responsive interactive terminal
    SOCKET_SELECT_TIMEOUT = 0.05  # 50ms - better balance between CPU and latency
    POLL_BACKOFF_MIN = 0.005  # 5ms minimum - more responsive
    POLL_BACKOFF_MAX = 0.2   # 200ms maximum - faster response when idle
    
    # Connection limits
    MAX_CONCURRENT_SESSIONS = 50
    CONNECTION_IDLE_TIMEOUT = 3600  # 1 hour
    
    # Logging
    LOG_BUFFER_SIZE_EVERY_N_READS = 100  # Reduce noisy logging

async def read_from_socket_safe(sock, max_size: int = WebSocketConfig.SOCKET_RECV_BUFFER) -> Optional[bytes]:
    """
    Read from socket using select for non-blocking I/O
    
    Args:
        sock: Socket object
        max_size: Max bytes to read
    
    Returns:
        bytes or None if no data available or error
    """
    try:
        loop = asyncio.get_event_loop()
        
        # Use select to wait for data with timeout
        readable, _, _ = select.select(
            [sock], [], [], 
            WebSocketConfig.SOCKET_SELECT_TIMEOUT
        )
        
        if readable:
            # Data available, read it
            data = await loop.run_in_executor(None, sock.recv, max_size)
            return data if data else None
        
        return None  # No data available
    
    except OSError as e:
        logger.debug("Socket read error: %s", str(e))
        return None
    except Exception as e:
        logger.warning("Unexpected error in read_from_socket_safe: %s", str(e))
        return None

async def write_to_socket_safe(sock, data: bytes) -> bool:
    """
    Write to socket safely
    
    Args:
        sock: Socket object
        data: Data to write
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, sock.sendall, data)
        return True
    except OSError as e:
        logger.debug("Socket write error: %s", str(e))
        return False
    except Exception as e:
        logger.warning("Unexpected error in write_to_socket_safe: %s", str(e))
        return False



def parse_control_message(data: str) -> dict | None:
    """
    Parse control messages from WebSocket data.
    Returns the parsed JSON dict if it's a valid control message, None otherwise.
    """
    try:
        json_data = json.loads(data)
        # Ensure json_data is a dictionary before returning
        if isinstance(json_data, dict):
            return json_data
        else:
            logger.debug("Received non-dict JSON data: %s (type: %s)", json_data, type(json_data).__name__)
            return None
    except json.JSONDecodeError:
        # Not valid JSON, will be treated as regular shell input
        return None
    except Exception as e:
        logger.warning("Unexpected error parsing JSON: %s", str(e))
        return None


@router.websocket("/ws/console/{container}")
async def websocket_console(websocket: WebSocket, container: str):
    """WebSocket endpoint for container terminal console - Optimized version
    
    Improvements:
    - Uses select() instead of fixed sleep polling
    - Adaptive backoff for reduced CPU usage
    - Better error handling and logging
    - Session tracking for debugging
    """
    await websocket.accept()
    
    session_id = f"{container}-{id(websocket)}"
    logger.info("WebSocket connection opened for container: %s (session: %s)", container, session_id)
    
    # Track session
    async with active_sessions_lock:
        if len(active_sessions) >= WebSocketConfig.MAX_CONCURRENT_SESSIONS:
            logger.warning("Max concurrent sessions reached (%d)", WebSocketConfig.MAX_CONCURRENT_SESSIONS)
            await websocket.send_json({"error": "Server at capacity, try again later"})
            await websocket.close()
            return
        
        active_sessions[session_id] = {
            "container": container,
            "started": time.time(),
            "bytes_sent": 0,
            "bytes_received": 0
        }
    
    # Initialize variables for cleanup in finally block
    sock = None
    exec_stream = None
    websocket_closed = False
    read_count = 0
    
    try:
        # Get container instance from Docker
        try:
            cont = docker_client.containers.get(container)
        except docker.errors.NotFound:
            logger.error("Container not found: %s", container)
            await websocket.send_json({"error": f"Container '{container}' not found"})
            await websocket.close()
            websocket_closed = True
            return
        except docker.errors.APIError as e:
            logger.error("Docker API error for container %s: %s", container, str(e))
            await websocket.send_json({"error": f"Docker error: {str(e)}"})
            await websocket.close()
            websocket_closed = True
            return
        
        # Load configuration and get shell type
        config_data = load_config()
        config = config_data["images"]
        image_name = to_display_name(container)

        if image_name not in config:
            logger.warning("Image '%s' not found in config for container %s", image_name, container)
            shell = "/bin/sh"
        else:
            shell = config.get(image_name, {}).get("shell", "/bin/bash")
        
        logger.info("Using shell %s for container %s", shell, image_name)
        
        # Get and format MOTD
        motd = get_motd(image_name, config) if image_name in config else ""
        formatted_motd = format_motd_for_terminal(motd)
        
        # Create exec instance in container
        try:
            exec_instance = docker_client.api.exec_create(
                container,
                shell,
                stdin=True,
                tty=True,
                environment={"TERM": "xterm-256color"}
            )
        except docker.errors.APIError as e:
            logger.error("Failed to create exec instance for container %s: %s", container, str(e))
            await websocket.send_json({"error": f"Failed to create console: {str(e)}"})
            await websocket.close()
            websocket_closed = True
            return
        
        # Start the exec instance
        try:
            exec_stream = docker_client.api.exec_start(
                exec_instance['Id'],
                socket=True,
                tty=True
            )
        except docker.errors.APIError as e:
            logger.error("Failed to start exec for container %s: %s", container, str(e))
            await websocket.send_json({"error": f"Failed to start console: {str(e)}"})
            await websocket.close()
            websocket_closed = True
            return
        
        # Get socket and set to non-blocking mode
        sock = exec_stream._sock
        sock.setblocking(False)
        
        logger.info("Console session started for container %s (session: %s)", container, session_id)
        
        # Send MOTD to client if available
        if formatted_motd:
            await asyncio.sleep(0.1)
            try:
                await websocket.send_text(formatted_motd)
                logger.info("Sent MOTD (%d characters) for image %s", len(formatted_motd), image_name)
            except Exception as e:
                logger.warning("Failed to send MOTD: %s", str(e))
        
        # ====================================================
        # READ TASK: Container → WebSocket (Optimized)
        # ====================================================
        async def read_from_container():
            """Read output from container and send to WebSocket client"""
            nonlocal read_count
            backoff = WebSocketConfig.POLL_BACKOFF_MIN
            bytes_sent_since_update = 0

            while True:
                try:
                    # Use select instead of sleep
                    data = await read_from_socket_safe(sock, WebSocketConfig.SOCKET_RECV_BUFFER)

                    if data:
                        try:
                            text = data.decode('utf-8', errors='replace')
                            await websocket.send_text(text)

                            # Batch session stats updates (update every 10KB to reduce lock contention)
                            bytes_sent_since_update += len(data)
                            if bytes_sent_since_update >= 10240:  # 10KB
                                async with active_sessions_lock:
                                    if session_id in active_sessions:
                                        active_sessions[session_id]["bytes_sent"] += bytes_sent_since_update
                                bytes_sent_since_update = 0

                            # Log every N reads to reduce noise
                            read_count += 1
                            if read_count % WebSocketConfig.LOG_BUFFER_SIZE_EVERY_N_READS == 0:
                                logger.debug("Session %s: read %d buffers", session_id, read_count)

                            # Reset backoff on successful read
                            backoff = WebSocketConfig.POLL_BACKOFF_MIN

                        except Exception as e:
                            logger.error("Error sending to WebSocket: %s", str(e))
                            break

                    else:
                        # No data available - adaptive backoff
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * 1.5, WebSocketConfig.POLL_BACKOFF_MAX)

                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected while reading (session: %s)", session_id)
                    # Flush remaining stats
                    if bytes_sent_since_update > 0:
                        async with active_sessions_lock:
                            if session_id in active_sessions:
                                active_sessions[session_id]["bytes_sent"] += bytes_sent_since_update
                    break
                except Exception as e:
                    logger.error("Error reading from container %s: %s", container, str(e))
                    break
        
        # ====================================================
        # WRITE TASK: WebSocket → Container (Optimized)
        # ====================================================
        async def write_to_container():
            """Read input from WebSocket client and send to container"""
            bytes_received_since_update = 0

            while True:
                try:
                    # Receive data from WebSocket client
                    data = await websocket.receive_text()
                    if data:
                        try:
                            # Try to parse as JSON for control messages
                            json_data = parse_control_message(data)

                            # Handle control messages (e.g., terminal resize)
                            if json_data and json_data.get("type") == "resize":
                                try:
                                    cols = int(json_data.get("cols", 80))
                                    rows = int(json_data.get("rows", 24))

                                    # Validate dimensions
                                    if cols <= 0 or rows <= 0:
                                        logger.warning("Invalid terminal dimensions: %dx%d", cols, rows)
                                        continue

                                    # Resize the exec instance
                                    docker_client.api.exec_resize(
                                        exec_instance['Id'],
                                        height=rows,
                                        width=cols
                                    )
                                    logger.debug("Resized terminal for %s: %dx%d", container, cols, rows)
                                    continue

                                except (ValueError, TypeError) as e:
                                    logger.warning("Invalid resize parameters: %s", str(e))
                                    continue
                                except Exception as e:
                                    logger.error("Error resizing terminal for %s: %s", container, str(e))
                                    continue

                            # Send regular input to container
                            if data and json_data is None:
                                success = await write_to_socket_safe(sock, data.encode('utf-8'))
                                if success:
                                    # Batch session stats updates (update every 1KB)
                                    bytes_received_since_update += len(data)
                                    if bytes_received_since_update >= 1024:  # 1KB
                                        async with active_sessions_lock:
                                            if session_id in active_sessions:
                                                active_sessions[session_id]["bytes_received"] += bytes_received_since_update
                                        bytes_received_since_update = 0
                                else:
                                    logger.error("Failed to write to socket")
                                    break

                            elif json_data and json_data.get("type") != "resize":
                                logger.debug("Unknown control message type: %s", json_data.get("type"))
                                success = await write_to_socket_safe(sock, data.encode('utf-8'))
                                if not success:
                                    break

                        except OSError as e:
                            logger.error("Socket error writing to container %s: %s", container, str(e))
                            break

                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected while writing (session: %s)", session_id)
                    # Flush remaining stats
                    if bytes_received_since_update > 0:
                        async with active_sessions_lock:
                            if session_id in active_sessions:
                                active_sessions[session_id]["bytes_received"] += bytes_received_since_update
                    break
                except Exception as e:
                    logger.error("Error writing to container %s: %s", container, str(e))
                    break
        
        # ====================================================
        # RUN BOTH TASKS CONCURRENTLY
        # ====================================================
        try:
            await asyncio.gather(
                read_from_container(),
                write_to_container(),
                return_exceptions=True
            )
        except Exception as e:
            logger.error("Error in console tasks for container %s: %s", container, str(e))
    
    except docker.errors.NotFound:
        logger.error("Container not found during session: %s", container)
        try:
            await websocket.send_json({"error": "Container not found"})
        except:
            pass
    
    except docker.errors.APIError as e:
        logger.error("Docker API error for container %s: %s", container, str(e))
        try:
            await websocket.send_json({"error": f"Docker error: {str(e)}"})
        except:
            pass
    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for container %s", container)
        websocket_closed = True
    
    except Exception as e:
        logger.error("Unexpected console error for container %s: %s", container, str(e))
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    
    finally:
        # Cleanup resources
        if sock:
            try:
                sock.close()
                logger.debug("Socket closed for container %s", container)
            except Exception as e:
                logger.warning("Error closing socket for container %s: %s", container, str(e))
        
        if exec_stream:
            try:
                exec_stream.close()
                logger.debug("Exec stream closed for container %s", container)
            except Exception as e:
                logger.warning("Error closing exec stream for container %s: %s", container, str(e))
        
        # Only close WebSocket if it hasn't been closed already
        if not websocket_closed:
            try:
                await websocket.close()
                logger.debug("WebSocket closed for container %s", container)
            except Exception as e:
                logger.debug("WebSocket already closed for container %s: %s", container, str(e))
        
        # Remove session tracking
        async with active_sessions_lock:
            if session_id in active_sessions:
                session_data = active_sessions[session_id]
                uptime = time.time() - session_data["started"]
                logger.info("Console session closed (session: %s, uptime: %.1fs, sent: %d bytes, recv: %d bytes)",
                           session_id, uptime, session_data["bytes_sent"], session_data["bytes_received"])
                del active_sessions[session_id]
        
        logger.info("Console session cleanup completed for container %s", container)

@router.get("/api/websocket-sessions")
async def get_websocket_sessions():
    """Get info about active WebSocket sessions (debug endpoint)
    
    Returns active console sessions with connection details and stats
    """
    async with active_sessions_lock:
        sessions_info = []
        for session_id, session_data in active_sessions.items():
            uptime = time.time() - session_data["started"]
            sessions_info.append({
                "session_id": session_id,
                "container": session_data["container"],
                "uptime_seconds": round(uptime, 1),
                "bytes_sent": session_data["bytes_sent"],
                "bytes_received": session_data["bytes_received"]
            })
        
        return {
            "total_active_sessions": len(sessions_info),
            "max_sessions": WebSocketConfig.MAX_CONCURRENT_SESSIONS,
            "sessions": sessions_info,
            "config": {
                "select_timeout": WebSocketConfig.SOCKET_SELECT_TIMEOUT,
                "buffer_size": WebSocketConfig.SOCKET_RECV_BUFFER,
                "backoff_min": WebSocketConfig.POLL_BACKOFF_MIN,
                "backoff_max": WebSocketConfig.POLL_BACKOFF_MAX
            }
        }