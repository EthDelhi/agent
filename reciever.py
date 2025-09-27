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
    
    # Store the response from agent2 in context storage
    ctx.storage.set('last_response', {
        'message': msg.message,
        'timestamp': time.time()
    })

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
    
    # Clear any old response
    ctx.storage.set('last_response', None)
    
    # Send message to agent2
    await ctx.send(AGENT2, Message(message=req.text))
    
    # Wait for a short time to get response from agent2
    max_retries = 5
    for _ in range(max_retries):
        stored_response = ctx.storage.get('last_response')
        if stored_response:
            # Get response and clear storage
            response = stored_response['message']
            ctx.storage.set('last_response', None)  # Clear the response
            
            return Response(
                text=f"Received: {req.text}",
                agent_address=ctx.agent.address,
                timestamp=int(time.time()),
                response_from_agent=response
            )
        await asyncio.sleep(2)  # Wait for response
    
    # If no response received
    return Response(
        text=f"Received: {req.text}",
        agent_address=ctx.agent.address,
        timestamp=int(time.time()),
        response_from_agent="No response from agent2"
    )
 

if __name__ == "__main__":
    ReceiverAgent.run()
 