 
from uagents import Agent, Context, Model
 
 
class Message(Model):
    message: str
 

agent = Agent(
    name="SenderAgent",
    port=8000,
    seed="SenderAgent secret phrase",
    endpoint=["http://127.0.0.1:8000/submit"],
)
 
print(agent.address)

@agent.on_message(model=Message)
async def message_handler(ctx: Context, sender: str, msg: Message):
    ctx.logger.info(f"Received message from {sender}: {msg.message}")
    
    # Process the message and send response back
    response = f"Agent2 processed: {msg.message}"
    await ctx.send(sender, Message(message=response))
 
if __name__ == "__main__":
    agent.run()
 