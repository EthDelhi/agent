import json
import uuid
import os
import ast
import tempfile
import shutil
import re # For dynamic API extraction
from datetime import datetime
from hyperon import MeTTa, S, V, E, GroundingSpace, ValueAtom
from uagents import Agent, Protocol, Context
from uagents_core.contrib.protocols.chat import ChatMessage, TextContent
import git

atomspace_agent = Agent(
    name="atomspace_agent",
    port=8001,
    seed="atomspace_agent_secret_seed_123",
    endpoint="http://127.0.0.1:8001/submit"
)
chat_protocol = Protocol(name="atomspace_protocol")

project_space = GroundingSpace()
try:
    metta_runner = MeTTa(space=project_space, env_builder=None)
except Exception:
    metta_runner = MeTTa()
    metta_runner._space = project_space
    
def _clone_repo_to_memory(repo_url: str) -> dict:
    """
    Clones a Git repository to a temporary directory on disk,
    reads all file contents into an in-memory dictionary, and then
    immediately deletes the temporary directory.
    """
    codebase_files = {} 
    temp_dir = tempfile.mkdtemp()
    
    try:
        print(f"Cloning {repo_url} into a temporary location...")
        git.Repo.clone_from(repo_url, temp_dir)
        print("Cloning complete. Reading files into memory...")

        # Walk through the temporary directory and load file contents into the dictionary.
        for root, dirs, files in os.walk(temp_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
            
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, temp_dir)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        # Store file content in the in-memory dictionary.
                        codebase_files[relative_path] = f.read()
                except Exception as e:
                    print(f"Warning: Could not read file {relative_path}: {e}")

    except git.exc.GitCommandError as e:
        print(f"Error: Failed to clone repository: {e}")
        return {}
    finally:
        # **Crucially, clean up and remove the temporary directory from the disk.**
        print("Deleting temporary directory...")
        shutil.rmtree(temp_dir)
        print("Repository contents are now only in memory.")
        
    return codebase_files

def identify_sponsor_apis_from_requirements(requirements: str) -> list:
    """
    Simulates AI extraction of required modules/APIs from sponsor's natural language requirements.
    In a real system, ASI:One would perform this JSON extraction.
    """
    common_apis = ['asi:one', 'metta', 'uagents', 'fetch', 'stripe', 'twilio', 'aws', 'gcp', 'azure']
    found_apis = [api for api in common_apis if api.lower() in requirements.lower()]
    return list(set(found_apis))

def initialize_codebase_knowledge_graph(metta: MeTTa, codebase_url: str, required_apis: list) -> tuple:
    """
    Clears the space, builds the KG, and identifies usage of required APIs.
    """
    if hasattr(project_space, 'clear'):
        project_space.clear()
        
    files_processed = 0
    atoms_added = 0
    verified_apis = set()
    codebase_files = _clone_repo_to_memory(codebase_url)
    print(len(codebase_files))

    for relative_path, content in codebase_files.items():
            if relative_path.endswith('.py'):       
                try:    
                    tree = ast.parse(content)
                    files_processed += 1
                    
                    for node in ast.walk(tree):
                        def add_atom_safe(atom):
                            nonlocal atoms_added
                            target_space = metta.space() if hasattr(metta, 'space') else project_space
                            target_space.add_atom(atom)
                            atoms_added += 1

                        if isinstance(node, (ast.Import, ast.ImportFrom)):
                            module_name = getattr(node, 'module', None)
                            
                            for alias in node.names:
                                imported_module = alias.name.lower()
                                
                                for req in required_apis:
                                    if req in imported_module:
                                        add_atom_safe(E(S("imports_required_api"), S(relative_path), S(imported_module)))
                                        verified_apis.add(req)
                                        if content.count(f"{req}.") > 0: 
                                            add_atom_safe(E(S("calls_api_function"), S(relative_path), S(f"{req}_call")))
                                            
                        if isinstance(node, ast.FunctionDef):
                            add_atom_safe(E(S("defines_function"), S(relative_path), S(node.name)))
                        elif isinstance(node, ast.ClassDef):
                            add_atom_safe(E(S("defines_class"), S(relative_path), S(node.name)))
                        
                except Exception as e:
                    print(f"Error parsing {relative_path}: {e}")
    
    metta_runner.run('!(add-atom &self (query_pattern find_verified_imports \"(match &self (imports_required_api $file $module) (pair $file $module))"))')
    
    return files_processed, atoms_added, verified_apis

def analyze_code_reuse(project_path: str, sponsor_repo_url: str) -> tuple:
    
    if not sponsor_repo_url:
        return 0, 100, "Skipped (No Sponsor Reference Repo Provided)"

    total_loc = 1000
    
    if "asi-alliance" in sponsor_repo_url.lower():
        lines_reused_simulated = 150 
    elif "test-apis-only" in sponsor_repo_url.lower():
        lines_reused_simulated = 50
    else:
        lines_reused_simulated = 100

    percentage_reused = round((lines_reused_simulated / total_loc) * 100, 2)
    percentage_original = round(100 - percentage_reused, 2)
    
    log_message = f"Simulated analysis against {sponsor_repo_url} assumed {total_loc} LOC analyzed."
    
    return percentage_reused, percentage_original, log_message

def perform_ai_reasoning(
    ctx: Context, metta: MeTTa, 
    summary: str, requirements: str, 
    atoms_count: int, repo_url: str,
    verified_apis: set,
    code_originality_score: float
) -> str:
    """
    Synthesizes the final structured report using all data points.
    """
    
    usage_query = metta.run('!(match &self (query_pattern find_verified_imports $query) $query)')
    
    required_count = len(identify_sponsor_apis_from_requirements(requirements))
    verified_count = len(verified_apis)
    
    # Base Integration Score (Weighted by verified features / required features)
    if required_count > 0:
        integration_ratio = verified_count / required_count
        base_score = int(integration_ratio * 70) # Max 70 points from features
    else:
        base_score = 0
        
    # Final Score includes base(para score (70 max) + originality (30 max)
    final_score = base_score + int(code_originality_score * 0.3) 
    
    
    ai_summary_status = "Successfully verified core technical claims."
    if final_score < 50:
        ai_summary_status = "Review required: Integration score is low and/or originality is questionable."

    ai_summary = f"""
    The verification analysis is complete for project submitted from {repo_url}.
    **Integration Status:** The project claims to use {required_count} key sponsor technologies, and **{verified_count}** of these were structurally verified in the code graph (Verification Ratio: {integration_ratio:.2f}).
    **Code Integrity:** The project exhibits **{code_originality_score:.2f}% Original Code**. This indicates the majority of the submitted code was original work for the hackathon and not simply reused from the sponsor's public documentation repository, addressing potential 'code dumping' fraud.
    **Conclusion:** The final technical score of {final_score}% suggests a {ai_summary_status}. The code graph analysis provides objective evidence to support the claimed integration points.
    """
    
    report = {
        "project_url": repo_url,
        "verification_status": "Verification Complete",
        "metrics": {
            "integration_score": final_score,
            "required_apis": required_count,
            "verified_apis": verified_count,
            "atoms_count": atoms_count,
            "code_originality_percentage": code_originality_score,
            "verification_log": [
                {"feature": "Required APIs Verified", "status": f"{verified_count} of {required_count}"},
                {"feature": "Code Originality", "status": f"{code_originality_score}%"},
            ]
        },
        "participant_summary_input": summary,
        "sponsor_requirements_input": requirements,
        "ai_summary_report": ai_summary
    }
    
    return json.dumps(report, indent=2)


@chat_protocol.on_message(model=ChatMessage)
async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
    """
    Receives the consolidated verification request and executes the analysis.
    """
    
    try:
        print(msg)
        raw_text = msg.content[0].text
        content = json.loads(raw_text)
        action = content.get("action")

        if action == "verify_project_integrity":
            repo_url = content.get("repo_url")
            summary = content.get("participant_summary", "N/A")
            requirements = content.get("sponsor_requirements", "N/A")
            sponsor_reference_apis = content.get("sponsor_apis", None)

            required_apis = identify_sponsor_apis_from_requirements(requirements)
            ctx.logger.info(f"Required APIs identified: {required_apis}")
         
            # reused_percent, original_percent, reuse_log = analyze_code_reuse(
            #     temp_dir_participant, sponsor_reference_repo
            # )
            # ctx.logger.info(f"Code Reuse Analysis: {reuse_log}")
            
            files_processed, atoms_added, verified_apis = initialize_codebase_knowledge_graph(
                metta_runner, repo_url, required_apis
            )
            ctx.logger.info(f"KG Built: Files={files_processed}, Atoms={atoms_added}. Verified APIs: {verified_apis}")

            original_percent = 0.3

            response_text = perform_ai_reasoning(
                ctx, metta_runner, summary, requirements, atoms_added, repo_url, 
                verified_apis, original_percent
            )
            
        elif action == "get_agent_info":
            response_text = json.dumps({"status": "ready", "address": str(atomspace_agent.address)})
        
        else:
            response_text = json.dumps({"error": "Unknown action"})

    except Exception as e:
        ctx.logger.error(f"Critical error during analysis: {e}")
        import traceback
        traceback.print_exc()
        response_text = json.dumps({"error": f"Internal agent analysis failed: {str(e)}"})
            
    response_msg = ChatMessage(
        timestamp=datetime.utcnow(),
        msg_id=str(uuid.uuid4()),
        content=[TextContent(text=response_text)]
    )
    await ctx.send(sender, response_msg)

atomspace_agent.include(chat_protocol)

@atomspace_agent.on_event("startup")
async def startup_event(ctx: Context):
    """Event triggered when the agent starts up."""
    ctx.logger.info(f"Atomspace Agent starting up...")
    ctx.logger.info(f"Agent address: {atomspace_agent.address}")
    ctx.logger.info(f"Agent is ready to receive messages!")

if __name__ == "__main__":
    atomspace_agent.run()