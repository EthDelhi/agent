import time
import asyncio
from uagents import Agent, Context, Model
from typing import Any, Dict

class Message(Model):
    message: str
 
AGENT2= "agent1qdw67s95esk0zwn8qxf0ln22e8zah9rqfrqqa4qyda7mjtpf3hsw640wuwr"
ReceiverAgent = Agent(
    name="ReceiverAgent",
    port=8001,
    seed="ReceiverAgent secret phrase",
    endpoint=["http://127.0.0.1:8001/submit"],
)
 
print(ReceiverAgent.address)
 

class Request(Model):
    text: str
    callback_url: str = None  # Optional callback URL for API responses
 
class Response(Model):
    timestamp: int
    text: str
    agent_address: str
    response_from_agent: str = None  # Response received from agent2

@ReceiverAgent.on_message(model=Message)
async def message_handler(ctx: Context, sender: str, msg: Message):
    ctx.logger.info(f"Received message from {sender}: {msg.message}")
    # Simply respond to confirm receipt
    await ctx.send(sender, Message(message="Message received"))

class EmptyMessage(Model):
    pass

@ReceiverAgent.on_rest_get("/rest/get", Response)
async def handle_get(ctx: Context) -> Dict[str, Any]:
    ctx.logger.info("Received GET request")
    return {
        "timestamp": int(time.time()),
        "text": "Hello from the GET handler!",
        "agent_address": ctx.agent.address,
    }
 
@ReceiverAgent.on_rest_post("/rest/post", Request, Response)
async def handle_post(ctx: Context, req: Request) -> Response:
    ctx.logger.info("Received POST request")
    
    # Send message to agent2 and wait for response
    reply, status = await ctx.send_and_receive(
        AGENT2,
        Message(message=req.text),
        response_type=Message
    )
    
    if isinstance(reply, Message):
        return Response(
            text=f"Received: {req.text}",
            agent_address=ctx.agent.address,
            timestamp=int(time.time()),
            response_from_agent=reply.message
        )
    else:
        return Response(
            text=f"Received: {req.text}",
            agent_address=ctx.agent.address,
            timestamp=int(time.time()),
            response_from_agent=f"Failed to get response: {status}"
        )
 

if __name__ == "__main__":
    ReceiverAgent.run()
 