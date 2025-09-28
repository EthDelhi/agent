curl -X POST http://127.0.0.1:8002/rest/post \
-H "Content-Type: application/json" \
-d '{
  "repo_url": "https://github.com/ishAN-121/Backend-for-Hermes",
  "participant_summary": "We have developed an AI bot using the uagent framework of ASA. We have also utilized the advanced reasoning capabilities of MeTTa knowledge graphs to have a structured database. A server has been setup and actions have been provided to the agent. A custom logic has been written to ensure that the output of agent is right.",
  "sponsor_requirements": "In order to qualify following apis must be used :
1) Agent
2)Protocol
3) Hyperon
4)Chatmessage
5)Context
"
}'