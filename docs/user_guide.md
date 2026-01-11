# AI Dashboard User Guide

This guide explains how to use the AI Autonomous Development Dashboard.

## 1. Dashboard Overview

The dashboard is divided into 5 main tabs:

### 📊 Pipeline
- **Real-time View**: Monitor active agents and their current tasks.
- **Queue/History**: Click on any agent card to open the Bottom Sheet.
  - **Queue Tab**: See pending tasks waiting for the agent.
  - **History Tab**: View past processing logs for that agent.

### 📜 Logs
- **System Logs**: View detailed logs from all system components.
- **Search & Filter**: Filter logs by Agent (e.g., `CODE`, `PLAN`) or Status (`INFO`, `ERROR`).

### ⏳ Pending
- **Action Required**: This tab lists items needing your attention.
  - **Clarification**: Agents asking for more info.
  - **Approval**: Critical actions (e.g., modifying files) needing permission.
  - **Debug Execution**: If Debug Mode is ON, tasks wait here for manual trigger.

### 📈 Stats
- **Performance Metrics**: View Token usage, Cost, and Task completion rates per agent.
- **Bottleneck Analysis**: Check which queues are backing up.

### ⚙️ Settings
- **System Configuration**: Manage LLM backends and RAG knowledge.

---

## 2. Key Features Guide

### 📂 RAG Repository Management
Train your agents on specific codebases.

1. Go to **Settings** > **Git 저장소 (RAG)**.
2. Enter a Git URL (e.g., `https://github.com/my/repo`).
3. Click **추가**.
4. The system will clone and index the code automatically (updates every 10 mins).
5. **Usage**: The `REQUIREMENT` agent will automatically search these repos to answer questions or plan tasks.

### 🐛 Debug Mode
Control the execution flow manually.

1. Go to **Settings**.
2. Toggle **디버깅 모드** ON.
3. **Effect**: Agents will NOT automatically pick up tasks.
4. Go to **Pending** tab to see waiting tasks.
5. Click **Approve/Run** to execute them one by one.

### 🤖 LLM Adapters
Switch AI models for specific agents.

1. Go to **Settings** > **LLM 설정**.
2. Select an adapter for each agent (e.g., `OpenAI`, `ClaudeCLI`, `CursorCLI`).
   - `ClaudeCLI`: Recommended for `CODE` agent (better coding).
   - `OpenAI`: Recommended for `PLAN`, `REQUIREMENT` (better logic).
3. Click **저장**.
