# **Forensicode: Automated Integrity and Technical Validation Platform**

## **The Problem Statement: Addressing the Crisis of Trust and Verification in Hackathons**

Hackathons are cornerstones of innovation, yet their integrity and judging efficiency are constantly challenged by two core issues: **Code Originality Fraud** and **Technical Claim Subjectivity**.

### **1\. The Integrity Crisis: Pre-Hacking and Cheating Detection**

Current hackathon judging relies heavily on trust and the limited human capacity of judges to spot sophisticated forms of cheating, such as "pre-hacking" (starting the project before the official timeline) or uneven team contributions.

* **The Time Constraint:** Judges have mere minutes to review a project, making a thorough manual audit of hundreds of commits across a repository virtually impossible.  
* **The Fairness Gap:** A project submitted with 90% pre-existing code fundamentally undermines the spirit of the event, yet this often goes undetected, disadvantling teams who build their projects entirely within the given timeline.  
* **Quantifying Effort:** There is no objective metric to quickly assess the distribution of coding work among team members, leading to subjective judging of individual contribution and team dynamics.

### **2\. The Verification Gap: Technical Requirement and API Usage Validation**

Sponsor challenges and specialized tracks often require the use of specific APIs, SDKs, or technologies. Verifying their correct and meaningful integration presents a significant hurdle.

* **Claim Inflation:** Teams may strategically mention a sponsor's API in their summary to qualify for a prize, even if the API is only imported but never utilized, or used in a trivial, non-functional way.  
* **Code Blindness:** Judges cannot definitively confirm if an imported function is actually called, if the logic is correct, or if the repository contains large amounts of unused or dead code that dilutes the actual hackathon work.  
* **The AI Summary Disconnect:** A discrepancy often exists between the participant's enthusiastically written project summary and the technical reality of the codebase.

**Forensicode** solves these critical problems by employing a multi-agent AI framework to conduct a deep, objective, and real-time audit of every submission, ensuring a level playing field for all participants.

## **The Solution: Forensicode — AI-Powered Audit and Validation**

Forensicode is a revolutionary, three-agent system designed to bring unprecedented transparency and objectivity to hackathon judging. It performs dual audits: **Integrity** (checking timeline adherence) and **Technical Implementation** (checking code quality and requirement fulfillment).

### **Architectural Overview**

![Full App Architecture](assets/all_flow.png)

### **Input Requirements**

Forensicode processes the following inputs for each submission:

1. **Project Repository Link (GitHub/GitLab)**  
2. **Official Hackathon Timeline (Start/End Timestamps)**  
3. **Sponsor/Track Requirements & APIs**  
4. **Participant Reasoning/Pitch on Track Qualification**  

### **Core Modules and AI Agents**

### **ASI Agents Flow**

![ASI Agent Flow](assets/ASI_flow.png)

#### **Module 1: The Integrity Agent (Commit History Auditor)**

This single-purpose AI Agent is dedicated to validating the originality and timeline compliance of the codebase.

| Component | Goal | Methodology & Resources |
| :---- | :---- | :---- |
| **Commit History Analysis** | Detect pre-work and unusual development patterns. | The agent uses two core principles: |
| **Timeline Check** | Validate that all significant work occurred during the event. | 1\. **MLH Cheating Guidelines:** Checks for large bursts of commits immediately before the event, commits dated outside the event window, and other suspicious patterns outlined by MLH. |
| **Contribution Score** | Quantify the code contribution percentage for each team member. | 2\. **Academic Algorithm (Goyal et al.):** Implements the logic from the paper ["Identifying unusual commits on GitHub"](https://www.researchgate.net/publication/319655637_Identifying_unusual_commits_on_GitHub_Goyal_et_al) to flag commits that are statistically anomalous in size, content, or timing. |
| **Output** | A **Pre-Hacking Confidence Score** and a visualized **Team Contribution Graph**. | All commits are visualized against the official timeline, and any commits falling outside are flagged and weighted heavily in the final integrity score. |

#### **Module 2: The Requirement Validation Pipeline (The Technical Agent Duo)**

This pipeline uses an inter-agent chat protocol to ensure both the *intent* and *implementation* of technical requirements are met.

##### **Agent 2a: The Extractor & Requester (asi11-mini)**

| Component | Goal | Methodology |
| :---- | :---- | :---- |
| **Requirement Parsing** | Extract specific, verifiable technical requirements (e.g., "Must use the Acme\_DB\_API"). | Uses the asi11-mini LLM to analyze the sponsor requirements text and the participant's reasoning, converting them into a structured JSON payload of **Required APIs and Functions**. |
| **Inter-Agent Protocol** | Prepare the audited data for the Code Graph Auditor. | The Extractor communicates this structured payload to Agent 2b via a chat protocol, facilitating a targeted audit request. |

##### **Agent 2b: The Auditor & Graph Generator (Knowledge Graph)**

| Component | Goal | Methodology & Technology |
| :---- | :---- | :---- |
| **Code Knowledge Graph Generation** | Create a verifiable map of the entire codebase's structure and dependencies. | Generates a **Knowledge Graph** (similar to **Falkor DB**) from the project repository using Metta-Knowledge Graph ASI code graph tooling. This graph maps classes, functions, files, imports, and cross-references. |
| **API Usage Verification (Source-Sink)** | Confirm that imported APIs are functionally used in the active logic. | Employs a **Breadth-First Search (BFS) algorithm** on the Code Graph. Starting from the imported API functions (**Source**), it traces dependencies to see if they flow into a main application routine or export (**Sink**). |
| **Code Utilization Metrics** | Identify code bloat and unfulfilled dependencies. | Checks for: <ul><li>APIs that were required and used (Success).</li><li>APIs that were required but only imported, not used.</li><li>Unused/Dead Code segments not connected to the main application flow.</li></ul> |

### **Final Output & Summary Comparison**

The final stage synthesizes all metrics into a unified dashboard and generates a final audit-based summary.

* **AI Summary Generation:** A final asi1-mini model is used to generate an **Objective Project Summary** based *only* on the verified and analyzed metrics from the code audit.  
* **Inflation Judgement:** This AI-generated summary is automatically compared (e.g., using semantic similarity scores) against the participant's submitted summary. The system outputs a **Summary Inflation Score**, directly quantifying how much the user's pitch exaggerated or misrepresented the project's technical reality.  
* **UI Dashboard:** All metrics—Integrity Score, API Usage Percentage, Team Contribution, and Inflation Score—are presented to the judge via clear graphs and visualizations for immediate, objective decision-making.

## **Justification and Online Resources**

Forensicode's methodologies are grounded in established industry practices for code analysis and academic research on fraudulent commit behavior.

| Metric/Methodology | Purpose | Resource |
| :---- | :---- | :---- |
| **Commit Integrity & Cheating Detection** | Adheres to community standards for fair competition and utilizes academic research to identify commit anomalies (e.g., large commits with pre-hackathon timestamps). | [MLH Cheating Check Guidelines](https://guide.mlh.io/general-information/judging-and-submissions/cheating-check) |
| **Identifying Unusual Commits** | Provides the specific algorithm and logic for flagging commits that are statistically anomalous in size, timing, or content. | [Identifying unusual commits on GitHub (Goyal et al.)](https://www.researchgate.net/publication/319655637_Identifying_unusual_commits_on_GitHub_Goyal_et_al) |
| **Code Graph & Technical Audit** | The concept of mapping code structure to analyze usage is foundational in compilers and static analysis tools like the open-source Falkor DB or similar Code Knowledge Graph technologies. | [Falkor DB Code Graph Documentation](https://www.falkordb.com/blog/code-graph/) |
