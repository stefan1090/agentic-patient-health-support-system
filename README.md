# Agentic Patient Health Support System

A modular patient-facing health support system that routes user questions to specialized response modules.

**Developer:** Stefan Escobar-Agreda, MD and MS in Biomedical and Health Informatics, focused on clinical AI evaluation.

## Overview

Recent literature suggests that healthcare LLM systems are commonly adapted through prompt engineering, fine-tuning, retrieval-augmented generation, or hybrid approaches [1].

This project explores whether an agentic routing-and-recovery design may be especially useful for realistic patient-facing inputs that are short, ambiguous, or mixed-intent [2].

Instead of treating every user message as the same generic task, the system first identifies the main type of need and then routes the request to the most appropriate response module. Urgent safety and emergency situations are handled separately through a top-level overlay.

## Routing taxonomy

The routing taxonomy in this repository was developed to capture common types of patient-facing health information needs.

The current content modules are:
- `clinical_assessment`
- `interpretation`
- `intervention`
- `management`
- `health_services`
- `education`

The system also applies a separate:
- `safety_overlay`
- `safety_level`

### Clinical assessment
Used for symptoms, signs, suspected illness, disease or condition mentions, abnormality, concern, or questions about whether something may be normal versus concerning.

### Interpretation
Used for lab results, imaging, questionnaire scores, screening scores, and diagnostic test findings.

### Intervention
Used for treatment-oriented questions, including medications, prescriptions, therapies, supplements, concrete interventions, treatment changes, and intervention-related safety considerations.

### Management
Used for practical actions, coping steps, day-to-day handling, implementation of a plan, and general low-risk management frameworks when the question is not centered on a specific intervention.

### Health services
Used for patient-facing health system navigation, including where to go, what type of provider or service is appropriate, referrals, access, insurance, coverage, benefits, eligibility, paperwork, and care pathways.

### Education
Used for health promotion, healthy habits, general health literacy, meanings of medical terms, abbreviations, and myths.

## Safety and emergency overlay

Urgent situations are handled separately from content routing.

The overlay covers:

- inability to stay safe
- risk of self-harm
- risk of harm to others
- severe behavioral disturbance with immediate danger
- abuse or violence with immediate danger
- acute medical emergencies
- other potentially life-threatening events

Examples include chest pain suggestive of heart attack, stroke symptoms, severe breathing difficulty, severe bleeding, major trauma, seizure emergency, loss of consciousness, or severe allergic reaction.

## Architecture

The system currently includes:

- **Rules router**: deterministic baseline and fallback
- **Stage 1 router**: main LLM-based routing layer
- **Stage 2 router**: secondary LLM-based recovery step for low-confidence cases
- **Orchestrator**: applies the safety overlay first, then prepares the selected response module

The second routing stage exists because many patient-facing inputs are not well-formed questions. They may be short, implicit, fragmentary, or ambiguous. In those cases, the system first assigns an initial route and confidence level, and if confidence is low, a second routing step summarizes the main topic of the message and helps recover a more appropriate route.

<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/958a0401-e5e9-4e92-b58e-da1eed561dbf" />

## Health services default context

The `health_services` module is designed to remain reusable, but when no country or health-system context is provided, it currently uses a general United States healthcare context by default.

This means the system may refer in general terms to pathways such as:

- primary care
- urgent care when clinically appropriate
- specialist referral pathways
- insurer member services
- county or state public health or behavioral health resources
- hospital or clinic patient navigation or social work support

Exact access, referral rules, eligibility, benefits, and paperwork may still vary by state, county, insurer, and health system. The intent is to provide a useful default rather than a vague “it depends” response.

## Safety and communication guardrails

The current modules include several general guardrails:

- **Clinical assessment** uses calm, non-alarmist language for highly stigmatized or commonly feared conditions
- **Intervention** emphasizes caution against self-medication, antimicrobial resistance, especially with prescription-only, controlled, or otherwise higher-risk medications
- **Education** is intentionally narrow and is not used as a broad fallback bucket for condition, evaluation, or intervention questions

## Demo dataset

The 10 demo cases included were extracted from HealthBench a public benchmark framework built around realistic health conversations for early testing and repository demos [3].

The sample is included to show:

- the expected input format
- how the routing pipeline behaves
- how to run the system in single-case and batch mode

## Repository structure

```text
data/
  outputs/
    test_10_outputs.csv
  test_10.csv

prompts/
  a1_clinical_assessment.txt
  a2_interpretation.txt
  a3_intervention.txt
  a4_management.txt
  a5_health_services.txt
  a6_education.txt
  emergency_overlay.txt
  global_rules.txt
  router_stage1.txt
  router_stage2.txt

scripts/
  run_batch.py
  run_one.py

src/
  export.py
  load_prompts.py
  orchestrator.py
  router.py
  router_llm.py
```

## How to run

From the repository root:

python3 scripts/run_one.py --routing-backend llm "I think I have a serious rash and I do not know if I should get checked"
python3 scripts/run_one.py --routing-backend rules "I think I have a serious rash and I do not know if I should get checked"

python3 scripts/run_batch.py --routing-backend llm
python3 scripts/run_batch.py --routing-backend rules

## Input format

The included demo batch file uses a small CSV example.

The system is intended to scale to larger datasets as long as they are converted into a compatible tabular structure, for example with a column containing the user message to be routed and processed.

## Current limitations

* the system has been tested in a sinthetic evaluation setting (Healthbench) rather than real-world patient deployment
* some module-boundary cases remain inherently debatable
* retrieval is not yet integrated
* service navigation defaults to a general U.S. context when no location or health-system context is provided
* local service details still require verification at the insurer, health-system, county, or state level

## Intended use

This repository is designed as a research and prototyping framework for:

* patient-facing health support
* modular clinical GenAI workflows
* evaluation of structured response strategies in health AI

It is intended to be adaptable to other specialties, domains, and country-specific health system contexts.

## References

1. Pingua B, et al. Medical LLMs: Fine-Tuning vs Retrieval-Augmented Generation. 2025.
2. Tran KT, Dao D, Nguyen MD, et al. Multi-Agent Collaboration Mechanisms: A Survey of LLMs. 2025.
3. Arora RK, Wei J, Soskin Hicks R, et al. HealthBench: Evaluating Large Language Models Towards Improved Human Health. 2025.
