from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import logging

from src.web.core.config import load_config, get_motd
from src.web.core.docker import docker_client
from src.web.utils.helpers import format_motd_for_terminal

router = APIRouter()
logger = logging.getLogger("uvicorn")

@router.websocket("/ws/console/{container}")
async def websocket_console(websocket: WebSocket, container: str):
    """WebSocket console endpoint"""
    await websocket.accept()
    logger.info("WebSocket opened for %s", container)
    
    try:
        cont = docker_client.containers.get(container)
        config_data = load_config()
        config = config_data["images"]
        
        image_name = container.replace("playground-", "", 1)
        shell = config.get(image_name, {}).get("shell", "/bin/bash")
        
        logger.info("Using shell %s for %s", shell, image_name)
        
        # Get MOTD
        motd = get_motd(image_name, config)
        formatted_motd = format_motd_for_terminal(motd)
        
        # Create exec instance
        exec_instance = docker_client.api.exec_create(
            container,
            shell,
            stdin=True,
            tty=True,
            environment={"TERM": "xterm-256color"}
        )
        
        exec_stream = docker_client.api.exec_start(
            exec_instance['Id'],
            socket=True,
            tty=True
        )
        
        sock = exec_stream._sock
        sock.setblocking(False)
        
        logger.info("Console session started for %s", container)
        
        # Send MOTD
        if formatted_motd:
            await asyncio.sleep(0.1)
            await websocket.send_text(formatted_motd)
            logger.info("Sent MOTD (%d chars) for %s", len(formatted_motd), image_name)
        
        async def read_from_container():
            """Read from container and send to websocket"""
            while True:
                try:
                    await asyncio.sleep(0.01)
                    try:
                        data = sock.recv(4096)
                        if data:
                            text = data.decode('utf-8', errors='replace')
                            await websocket.send_text(text)
                    except BlockingIOError:
                        continue
                except Exception as e:
                    logger.error("Error reading from container: %s", str(e))
                    break
        
        async def write_to_container():
            """Read from websocket and send to container"""
            while True:
                try:
                    data = await websocket.receive_text()
                    if data:
                        sock.send(data.encode('utf-8'))
                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected")
                    break
                except Exception as e:
                    logger.error("Error writing to container: %s", str(e))
                    break
        
        await asyncio.gather(
            read_from_container(),
            write_to_container(),
            return_exceptions=True
        )
    
    except docker.errors.NotFound:
        await websocket.send_json({"error": "Container not found"})
    except Exception as e:
        logger.error("Console error for %s: %s", container, str(e))
        await websocket.send_json({"error": str(e)})
    finally:
        try:
            sock.close()
        except:
            pass
        try:
            await websocket.close()
        except:
            pass
        logger.info("Console session closed for %s", container)