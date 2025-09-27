from uagents import Agent, Context, Model
from uagents_core.contrib.protocols.chat import ChatMessage, TextContent
from datetime import datetime
import uuid
import json
from typing import Any, Dict
import asyncio
import time
import os
from dotenv import load_dotenv
import requests

class Request(Model):
    repo_url :str
    participant_summary : str
    sponsor_requirements : str

class Response(Model):
    text : str
    agent_address : str
    timestamp : int
    response_from_agent : Dict

class Message(Model):
    timestamp: int
    text: str
    content: TextContent
 
load_dotenv()

ATOMSPACE_AGENT_ADDRESS = "agent1qfveg6xj53uaw97e3gcyp5uttfmrh5z939kv83z4vp8kjz3fpw3q585wquc"
VERIFICATION_AGENT_SEED = "project verification agent unique seed"
ASI_ONE_API_KEY = os.getenv("ASI_ONE_API_KEY")


verification_agent = Agent(
    name="verification_agent",
    seed=VERIFICATION_AGENT_SEED,
    port=8002,
    endpoint="http://127.0.0.1:8002/submit"
)

received_responses = []

@verification_agent.on_rest_post("/rest/post", Request, Response)
async def handle_post(ctx: Context, req: Request) -> Response:
    ctx.logger.info(req)
   

    list_apis=identify_sponsor_apis_from_requirements(requirements=req.sponsor_requirements)
    payload = {
        "action": "verify_project_integrity",
        "repo_url": req.repo_url,
        "participant_summary": req.participant_summary,
        "list_apis": list_apis,
    }
    chat_message = ChatMessage(
        timestamp=datetime.utcnow(),
        msg_id=str(uuid.uuid4()),
        content=[TextContent(text=json.dumps(payload))]
    )
    reply, status = await ctx.send_and_receive(
        ATOMSPACE_AGENT_ADDRESS,
        chat_message,
        response_type=ChatMessage
    )

    final_report = reply.content[0].text if reply.content else "{}"
    json_report=json.loads(final_report)    
    return Response(
        text=f"Successfully received report for: {req.repo_url}",
        agent_address=ctx.agent.address,
        timestamp=int(time.time()),
        response_from_agent=json.loads(final_report) 
)


@verification_agent.on_event("startup")
async def startup(ctx: Context):
    print(f"Verification Agent starting up...")
    print(f"Agent address: {verification_agent.address}")
    await asyncio.sleep(2)
   # await start_verification_workflow(ctx)

def identify_sponsor_apis_from_requirements(requirements: str) -> list:
    """
    Simulates AI extraction of required modules/APIs from sponsor's natural language requirements.
    In a real system, ASI:One would perform this JSON extraction.
    """

    requirements = requirements.lower()

    prompt = """You are an expert software engineer specializing in automated requirement analysis. Your task is to meticulously extract all mentioned APIs, libraries, SDKs, and specific function names from the provided sponsor requirements.

        ### INSTRUCTIONS
        1.  **Identify Technologies**: Scan the text for names of specific software products, APIs, libraries, or SDKs (e.g., "Twilio", "Stripe", "Firebase", "Topsis").
        2.  **Identify Functions**: Scan the text for explicitly named functions (e.g., `calculate_score()`, `.create()`, `process_payment`).
        3.  **Format the Output**: Return a single, valid JSON object. Do not include any text or explanation outside of the JSON object.
        4.  **JSON Structure**: The JSON object must contain two keys: `apis_sdk_classes_and_libraries` and `functions`. The value for each key must be a list of strings.
        5.  **Normalization**: All extracted names should be in lowercase.
        6.  **Empty Lists**: If no APIs or functions are found, the value for the corresponding key must be an empty list `[]`.

        ### EXAMPLE
        **Input Text:**
        This challenge requires integration of two key external components:
        1. The project must use the Topsis library for multi-criteria decision analysis.
        2. All user payment data must be processed using the Stripe API, specifically by calling the `stripe.Charge.create()` method.

        **Output JSON:**
        ```json
        {
        "`apis_sdk_classes_and_libraries": [
            "topsis",
            "stripe"
        ],
        "functions": [
            "stripe.charge.create"
        ]
        }
        TASK
        Now, process the following requirements text according to the instructions and example above.
        Input Text: 
        """
    try:
        url = "https://api.asi1.ai/v1/chat/completions"
        headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ASI_ONE_API_KEY}",
            }

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": requirements},
            ]

        data = {"model": "asi1-mini", "messages": messages}

        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            raise Exception(f"ASI.AI API error: {response.status_code}")

        result = response.json()
        print('\nAPI Response:', json.dumps(result, indent=2))
        if not result.get('choices') or not result['choices'][0].get('message'):
            raise Exception('Invalid API response format')
            
        content = result['choices'][0]['message']['content']
        print('\nLLM Output:', content)
        list = json.loads(content[7:-3])
        return list['apis_sdk_classes_and_libraries']

    except Exception as e:
        print("Error:" , e)

if __name__ == "__main__":
    verification_agent.run()