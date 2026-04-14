# Custom Host Requirements Guide

This guide describes how to create and use custom host requirements for Deadline Cloud rendering in Unreal Engine.

## Overview

Host Requirements define which fleet are eligible to run a particular render step.
They are stored inside a `UDeadlineCloudHostRequirements` asset, which is then referenced by a `DeadlineCloudRenderStep` asset.

| Requirement Type | Configuration Location | Use Case |
|------------------|------------------------|----------|
| Base System Requirements | CPU / RAM / GPU fields | Restrict rendering to machines with specific hardware |
| Custom Amount Requirements | Name + Min/Max values | Require numeric resource levels (licenses, tokens, quotas) |
| Custom Attribute Requirements | Attribute + value list | Required custom attributes on fleets to run the step |

> Hiding a requirement using the eye icon only hides it in the MRQ Submit UI.  
> The requirement **still applies** when submitting the job.
> 
> **Important:** 
> The `Name` and `Attribute` values used for **Custom Amount Requirements** and  
> **Custom Attribute Requirements** must strictly match the valid identifiers  
> defined in the official Open Job Description documentation:  **[Open Job Specifications](https://github.com/OpenJobDescription/openjd-specifications/wiki/2023-09-Template-Schemas#33-hostrequirements)**

---

## Step 1: Create the Host Requirements Asset

1. Open Content Browser in Unreal Engine.
2. Create a new asset:
   Add → Miscellaneous → Data Asset → DeadlineCloudHostRequirements
3. Name the asset, e.g. `MyHostRequirements`.

---

## Step 2: Load the Default YAML Template

1. In the asset details panel, locate the field **Path to Template**.
2. Select the default template:
   Plugins/UnrealDeadlineCloudService/Content/Python/openjd_templates/host_requirements.yml

This loads base requirements such as CPU, Memory, GPU, OS, and architecture.

> Base requirements cannot be removed; only their values may be changed.

---

## Step 3: Configure Base (System) Requirements

| Setting | Example |
|--------|---------|
| Operating System | `windows` |
| CPU Architecture | `x86_64` |
| vCPUs (Min) | `16` |
| GPUs (Min) | `1` |

If Max = 0, then there is **no upper limit** for that requirement.

---

## Step 4: Add Custom Amount Requirements

Used when the requirement is numeric (e.g., number of licenses, concurrency limits).

1. Find the section **Custom Amount Requirements**.
2. Add a new entry and set a name, for example:
   `amount.custom.license`
3. Set Min and Max values:
   - Min: 1  
   - Max: 0 (0 means unlimited)

---

## Step 5: Add Custom Attribute Requirements

Used to filter workers based on tags and labels.

1. Find the section **Custom Attributes Requirements**.
2. Add a new attribute name, for example:
   `attr.custom.gpu.vendor`
3. Choose the matching rule:
   - **AllOf** — all values must match
   - **AnyOf** — at least one must match
4. Enter attribute values separated by spaces, for example:
   `nvidia amd`

---

## Step 6: Visibility in MRQ (Optional)

Each requirement entry has an **eye** icon.

| Eye | Behavior |
|-----|----------|
| Visible | The requirement is shown in MRQ Submit UI |
| Hidden | The requirement is hidden but **still included** when submitting the job |

This is useful for simplifying UI for artists while preserving technical constraints.

---

## Step 7: Attach the Requirements to a Render Step

1. Open the relevant `DeadlineCloudRenderStep` asset.
2. Find the **Host Requirements** field.
3. Assign your created asset (e.g., `MyHostRequirements`).

All MRQ submissions using this step will now enforce your host selection logic.

---

## Summary

Using the Host Requirements asset, you can:

- Control which worker machines execute your render jobs
- Specify minimum resource levels
- Target specific worker pools via attribute matching
- Simplify UI while keeping technical rules intact
- Reuse settings across multiple MRQ steps

This improves job routing consistency and ensures rendering happens on the correct hardware.

