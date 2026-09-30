---
name: ue-dev-setup
description: Automated dev environment setup for deadline-cloud-for-unreal-engine. Use when onboarding, setting up the UE integration repo, building the plugin, or installing dependencies. The agent automates all steps and only prompts when user input is required.
tags: [skill, deadline-cloud, deadline-cloud-for-unreal-engine deadline-cloud-for-ue, dev-setup, onboarding, dev-setup, plugin-build]
---

# Unreal Engine Dev Setup

## Overview

AI-guided automated setup for the `deadline-cloud-for-unreal-engine` project. The agent executes all steps, validates results, and only prompts the user when manual intervention is truly required.

## Usage

Use this skill when:
- Setting up a new dev environment for the UE integration
- Onboarding to the `deadline-cloud-for-unreal-engine` repo
- Building the C++ plugin or Python packages for the first time

## Core Concepts

**Platform:** Windows only. UE 5.4–5.8, Python 3.9+.

**Build system:** Hatch (Python), Unreal Build Tool (C++)

## Agent Behavior

You **MUST** automate all possible steps by running commands directly.
You **MUST** only prompt the user when their input is required (fork URL, UE version, custom paths).
You **MUST** validate each step's output before proceeding to the next.
You **MUST** inform the user clearly when manual intervention is needed (e.g., installing Visual Studio).
You **SHOULD** report progress at each step.

## Setup Workflow

Follow the detailed step-by-step workflow in [references/setup-guide.md](references/setup-guide.md).

Summary of steps:
1. Verify Windows OS (abort if not Windows)
2. Check GPU and NVIDIA drivers
3. Enable Windows Long Paths
4. Verify Python 3.9+ (attempt install via winget if missing)
5. Verify Visual Studio with C++ tools
6. Verify Deadline Cloud Monitor / CLI
7. Detect Unreal Engine installation
8. Install Hatch
9. Build and install plugin (`python scripts/build_plugin.py --install`)
10. Verify environment variables on PATH
11. Display summary
12. Instruct user to enable plugin in UE
