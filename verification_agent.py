from uagents import Agent, Context, Model
from uagents_core.contrib.protocols.chat import ChatMessage, TextContent
from datetime import datetime
import uuid
import json
from typing import Any, Dict
import asyncio

class Request(Model):
    text: str
 
class Response(Model):
    timestamp: int
    text: str
    agent_address: str
 

ATOMSPACE_AGENT_ADDRESS = "agent1qfveg6xj53uaw97e3gcyp5uttfmrh5z939kv83z4vp8kjz3fpw3q585wquc"
VERIFICATION_AGENT_SEED = "project verification agent unique seed"
VERIFICATION_API_KEY = "sk_f7436e51471d472ca7e613980b172a6d1f80b9fa0725479b80c3cc5c906e2d92" 

verification_agent = Agent(
    name="verification_agent",
    seed=VERIFICATION_AGENT_SEED,
    port=8002,
    endpoint="http://127.0.0.1:8002/submit"
)

received_responses = []

MOCK_GITHUB_REPO = "https://github.com/ishAN-121/APDP-Implementation"
SPONSOR_REFERENCE_REPO = "https://github.com/SponsorCorp/test-apis-only.git" 
SPONSOR_REQUIREMENTS = """
This challenge requires integration of two key external components:
1. The project must use the 'twilio' SMS API for user notification.
2. The project must store user data using the 'firebase' module/SDK.
3. Bonus points for using the 'MeTTa' knowledge graph for complex reasoning.
"""
PARTICIPANT_SUMMARY = """
We used the twilio API for immediate SMS alerts and Firebase to manage user profiles. The logic employs a custom graph database for decision making.
"""
@verification_agent.on_rest_post("/submit", Request, Response)
async def handle_post(ctx: Context, req: Request) -> Response:
    ctx.logger.info(req)
    return Response(...)


@verification_agent.on_event("startup")
async def startup(ctx: Context):
    print(f"Verification Agent starting up...")
    print(f"Agent address: {verification_agent.address}")
    await asyncio.sleep(2)
    await start_verification_workflow(ctx)

@verification_agent.on_message(model=ChatMessage)
async def handle_response(ctx: Context, sender: str, msg: ChatMessage):
    """
    Handles the final report sent back by the Atomspace Agent.
    """
    print(f"\n===========================================")
    print(f"=== FINAL REPORT RECEIVED FROM {sender} ===")
    print(f"===========================================")
    
    try:
        if msg.content and len(msg.content) > 0:
            content_text = msg.content[0].text
            response_data = json.loads(content_text)
            
            metrics = response_data.get('metrics', {})
            
            print(f"VERIFICATION STATUS: {response_data.get('verification_status')}")
            print(f"INTEGRATION SCORE: {metrics.get('integration_score')}%")
            print(f"CODE ORIGINALITY: {metrics.get('code_originality_percentage')}%")
            print(f"VERIFIED APIs: {metrics.get('verified_apis')} of {metrics.get('required_apis')}")
            
            # Display the AI-Generated Summary
            print("\n--- AI REASONING SUMMARY ---")
            print(response_data.get('ai_summary_report', 'N/A'))
            
            # Display detailed log for UI rendering
            print("\n--- VERIFICATION LOG ---")
            for log in metrics.get('verification_log',):
                print(f"  - {log['feature']}: {log['status']}")
            
            received_responses.append(response_data)
        else:
            print("Empty content received")
            
    except json.JSONDecodeError as e:
        ctx.logger.error(f"Error decoding JSON response: {e}")
        print(f"Raw response: {msg.content.text if msg.content else 'N/A'}")
    except Exception as e:
        ctx.logger.error(f"An unexpected error occurred during message handling: {e}")

async def start_verification_workflow(ctx: Context):
    """
    Initiates the comprehensive verification process for a project.
    """

    payload = {
        "action": "verify_project_integrity",
        "repo_url": MOCK_GITHUB_REPO,
        "participant_summary": PARTICIPANT_SUMMARY,
        "sponsor_requirements": SPONSOR_REQUIREMENTS,
        "sponsor_apis": SPONSOR_REFERENCE_REPO,
    }

    print(f"\n>>> Starting Verification for {MOCK_GITHUB_REPO} <<<")
    
    chat_message = ChatMessage(
        timestamp=datetime.utcnow(),
        msg_id=str(uuid.uuid4()),
        content=[TextContent(text=json.dumps(payload))]
    )
    
    await ctx.send(ATOMSPACE_AGENT_ADDRESS, chat_message)
    print(f"Request sent to Atomspace Agent successfully!")

if __name__ == "__main__":
    verification_agent.run()