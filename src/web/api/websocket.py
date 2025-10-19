from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import logging
import docker
import json

from src.web.core.config import load_config, get_motd
from src.web.core.docker import docker_client
from src.web.utils.motd_processor import format_motd_for_terminal

router = APIRouter()
logger = logging.getLogger("uvicorn")


@router.websocket("/ws/console/{container}")
async def websocket_console(websocket: WebSocket, container: str):
    """WebSocket endpoint for container terminal console"""
    await websocket.accept()
    logger.info("WebSocket connection opened for container: %s", container)
    
    # Initialize variables for cleanup in finally block
    sock = None
    exec_stream = None
    websocket_closed = False  # Track WebSocket closure state
    
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
        
        # Extract image name from container name
        image_name = container.replace("playground-", "", 1)
        
        # Determine which shell to use based on configuration
        if image_name not in config:
            logger.warning("Image '%s' not found in config for container %s", image_name, container)
            shell = "/bin/sh"  # Default fallback shell
        else:
            shell = config.get(image_name, {}).get("shell", "/bin/bash")
        
        logger.info("Using shell %s for container %s", shell, image_name)
        
        # Get and format MOTD (Message of the Day)
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
        
        logger.info("Console session started for container %s", container)
        
        # Send MOTD to client if available
        if formatted_motd:
            await asyncio.sleep(0.1)  # Small delay to ensure client is ready
            try:
                await websocket.send_text(formatted_motd)
                logger.info("Sent MOTD (%d characters) for image %s", len(formatted_motd), image_name)
            except Exception as e:
                logger.warning("Failed to send MOTD: %s", str(e))
        
        async def read_from_container():
            """Read output from container and send to WebSocket client"""
            while True:
                try:
                    await asyncio.sleep(0.01)  # Small delay to prevent busy waiting
                    try:
                        # Read data from container socket
                        data = sock.recv(4096)
                        if data:
                            # Decode and send to WebSocket client
                            text = data.decode('utf-8', errors='replace')
                            await websocket.send_text(text)
                        else:
                            # Socket closed by container
                            logger.info("Container socket closed for %s", container)
                            break
                    except BlockingIOError:
                        # No data available, continue polling
                        continue
                    except OSError as e:
                        # Socket error occurred
                        logger.error("Socket error reading from container %s: %s", container, str(e))
                        break
                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected while reading from container %s", container)
                    break
                except Exception as e:
                    logger.error("Error reading from container %s: %s", container, str(e))
                    break
        
        async def write_to_container():
            """Read input from WebSocket client and send to container"""
            while True:
                try:
                    # Receive data from WebSocket client
                    data = await websocket.receive_text()
                    if data:
                        try:
                            # Try to parse as JSON for control messages
                            try:
                                json_data = json.loads(data)
                                if json_data.get("type") == "resize":
                                    cols = int(json_data.get("cols", 80))
                                    rows = int(json_data.get("rows", 24))
                                    # Resize the exec instance
                                    docker_client.api.exec_resize(
                                        exec_instance['Id'],
                                        height=rows,
                                        width=cols
                                    )
                                    logger.debug("Resized terminal for %s: %dx%d", container, cols, rows)
                                    continue  # Skip sending resize to container
                            except json.JSONDecodeError:
                                pass  # Not a JSON message, treat as regular input
                            
                            # Send regular input to container
                            sock.send(data.encode('utf-8'))
                        except OSError as e:
                            logger.error("Socket error writing to container %s: %s", container, str(e))
                            break
                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected while writing to container %s", container)
                    break
                except Exception as e:
                    logger.error("Error writing to container %s: %s", container, str(e))
                    break
        
        # Run both read and write tasks concurrently
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
            pass  # Client may have already disconnected
    
    except docker.errors.APIError as e:
        logger.error("Docker API error for container %s: %s", container, str(e))
        try:
            await websocket.send_json({"error": f"Docker error: {str(e)}"})
        except:
            pass  # Client may have already disconnected
    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for container %s", container)
        websocket_closed = True
    
    except Exception as e:
        logger.error("Unexpected console error for container %s: %s", container, str(e))
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass  # Client may have already disconnected
    
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
        else:
            logger.debug("WebSocket was already closed for container %s", container)
        
        logger.info("Console session closed for container %s", container)