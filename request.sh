curl -X POST http://127.0.0.1:8002/rest/post \
-H "Content-Type: application/json" \
-d '{
  "repo_url": "https://github.com/ishAN-121/APDP-Implementation",
  "participant_summary": "We used the topsis for immediate SMS alerts and Firebase to manage user profiles. The logic employs a custom graph database for decision making.",
  "sponsor_requirements": "This challenge requires integration of two key external components:1. The project must use the Topsis SMS API for user notification.2. The project must use PDP user data using the firebase module/SDK.3. Bonus points for using the MeTTa knowledge graph for complex reasoning."
}'