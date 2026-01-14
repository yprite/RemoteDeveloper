# Self-Improvement & Real Development Guide

This system is now capable of performing autonomous coding tasks on actual repositories, including its own codebase.

## Prerequisites
1. **OpenAI API Key**: Ensure `OPENAI_API_KEY` is set in your `.env` file.
2. **Git Credentials**: The environment where the backend runs must have Git credentials configured to push to the target repository (e.g., SSH keys or Credential Helper).

## How It Works
The standard agent pipeline (Idea -> Requirements -> Plan -> UI -> Architect -> Code) has been upgraded:
- **Agents** now use Real LLM (OpenAI) to generate content instead of placeholders.
- **Code Agent** produces actual code files and commits them to a git branch.

## Triggering a Task

You can trigger a task via the API endpoint `/event/ingest`.

### payload Example for "Self-Improvement"
To make the agent improve *this* project:

```json
POST /event/ingest
{
  "task": {
    "original_prompt": "Add a new feature to the logging system that saves logs to a file.",
    "git_context": {
      "repo_url": "https://github.com/your-username/RemoteDevelop.git",
      "custom_path": null
    }
  }
}
```

### Flow
1. **Requirement**: Refines the prompt using LLM.
2. **Plan/UI/Arch**: Generates design docs using LLM.
3. **Code**:
   - Clones the repo to `../workspace_tasks/task_{id}`.
   - Creating a branch `feature/task_{id}`.
   - Generates code files via LLM.
   - Commits changes.
4. **Result**: You will see a new branch in your repo. Merge it to apply changes.

## Configuration
- **Model**: Defaults to `gpt-4o`. Configurable in `backend/core/llm.py`.
- **Workspace**: Temp repos are stored in `../workspace_tasks/`.
