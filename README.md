# Agentic Patient Health Support System

A multi-agent patient-facing health support system designed to improve utility and safety by routing health questions to specialized agents.

**Developer:** Stefan Escobar, Physician and Master in Biomedical Informatics, focused on clinical AI evaluation.

## What this project does

This project explores a routing-first alternative to monolithic healthcare chatbots.

Instead of treating every user query as one generic chatbot task, the system classifies the question first and routes it to the most appropriate specialized agent. It also separates urgent safety and emergency situations through a top-level overlay.

The goal is to improve:

- **utility**, by reducing unnecessary refusal and making responses more relevant
- **safety**, by prioritizing urgent situations separately
- **precision**, by matching the response strategy to the actual type of patient question

## Why a multi-agent system?

Patient-facing health questions are heterogeneous. A single chatbot may need to handle:

- symptoms and suspected conditions
- test results
- treatment questions
- practical coping and day-to-day management
- health system navigation
- prevention and health literacy
- urgent safety or emergency situations

These needs require different levels of caution, structure, and actionability. This project uses a multi-agent design so each type of request can be handled more appropriately.

## Routing taxonomy

The current content agents are:

- `clinical_assessment`
- `interpretation`
- `intervention`
- `management`
- `health_services`
- `education`

The system also applies a separate:

- `safety_overlay`
- `safety_level`

### Clinical Assessment
Symptoms, suspected illness, disease-specific questions, worsening, relapse, progression, or clinical meaning of a condition.

### Interpretation
Lab results, imaging, questionnaire scores, and diagnostic test findings.

### Intervention
Questions centered on a specific intervention, such as medications, dose changes, therapies, supplements, or other concrete treatments.

### Management
Practical actions, coping steps, day-to-day handling, implementation of a plan, or what to do right now.

### Health Services
Patient-facing health system navigation, including referrals, access, specialists, insurance, coverage, eligibility, paperwork, and care pathways.

### Education
Prevention, health promotion, healthy habits, health literacy, term meanings, abbreviations, and myths.

## Safety / emergency overlay

Urgent situations are handled separately from content routing.

The overlay covers:
- suicide or self-harm risk
- inability to stay safe
- harm to others
- psychosis or severe behavioral disturbance with danger
- abuse or violence with immediate danger
- acute medical emergencies or potentially life-threatening events

Examples include chest pain suggestive of heart attack, stroke symptoms, severe breathing difficulty, major trauma, severe bleeding, seizure emergency, loss of consciousness, or severe allergic reaction.

## Architecture

The system currently includes:

- **Rules router**: deterministic baseline and fallback
- **LLM router**: main routing backend
- **Orchestrator**: applies the safety/emergency overlay first, then prepares the selected agent prompt

This is an **LLM-first** design with a rules-based fallback for robustness and debugging.

## Evaluation

The prototype has been tested on an initial set of **10 curated realistic health queries** using HealthBench-style cases for early routing validation.

The goal of this initial evaluation was not to overfit to a benchmark, but to test whether the routing logic behaves sensibly across:

- mixed-intent health questions
- symptom-based queries
- intervention questions
- navigation questions
- practical management requests
- safety and emergency scenarios

The current system has reached a stable point where most remaining disagreements are **boundary cases**, not major architectural failures.

## Repository structure

```text
data/
  outputs/
    test_10_outputs.csv
  test_10.csv

prompts/
  clinical_assessment.txt
  education.txt
  emergency_overlay.txt
  global_rules.txt
  health_services.txt
  interpretation.txt
  intervention.txt
  management.txt
  router_agent.txt
  router.txt

scripts/
  run_batch.py
  run_one.py

src/
  export.py
  load_prompts.py
  orchestrator.py
  router_llm.py
  router.py
```

## How to run

From the repository root:

```bash
python3 scripts/run_one.py --routing-backend llm "I think I have postpartum depression"
python3 scripts/run_one.py --routing-backend rules "I think I have postpartum depression"
python3 scripts/run_batch.py --routing-backend llm
python3 scripts/run_batch.py --routing-backend rules
```

## Current limitations

- evaluation is still small and curated
- routing is currently more mature than downstream full-answer generation
- some agent-boundary ambiguities remain
- caregiver framing is important but not yet formalized in the schema
- no integrated retrieval or full RAG pipeline yet
- no large-scale benchmark run yet

## Why this matters

Most healthcare chat systems are still built as one chatbot with one generalized answer style.

This project explores a more structured alternative:
a **patient-facing multi-agent health support architecture** that separates safety/emergency handling from content-specific routing and aims to improve both utility and safety.

## References

- Nature Health paper on public use of a generalist LLM chatbot for health queries
- HealthBench
- OpenAI healthcare / HealthBench materials
