# Mitchi AI

<p align="center">
  <img width="250" height="250" src="https://github.com/user-attachments/assets/f257c518-1803-4d70-9abb-c86e54da88cf"
 />
</p>


**Your Local AI Productivity Agent**  
Mitchi AI is a **local-first, privacy-respecting AI assistant** that sits on your machine like a chill, command-reactive cat. Built as a modular, extensible desktop agent, Mitchi can connect to your favorite tools (Gmail, GitHub, Reddit, Weather, Shell, etc.) and perform intelligent actions on your command using LLMs but it never does anything behind your back


---

## Overview

---
Mitchi comes with a suite of both internal and external tools:

### Internal Tools
- Shell command execution
- Local file reading and summarization
- Web scraping and summarization
- Memory manager (note, recall, update)
- Local goal/task management

### External Tools (OAuth-enabled)
- Gmail: Read, send, summarize, manage emails
- GitHub: View PRs, issues, notifications
- Reddit: Fetch and summarize threads, sentiment detection
- AccuWeather: Get current weather and forecasts
- Google Maps: Location search and basic directions
- CoinGecko: Crypto price tracking
- Calendar & Notion: Scheduling and knowledge access

Each external integration requires explicit user login via OAuth. Mitchi never accesses anything without permission.

## Technology Stack

| Component          | Technologies                              |
|--------------------|-------------------------------------------|
| Frontend           | React, Tailwind CSS, GSAP                 |
| AI Engine          | Python, Gemma3:4b, LangGraph              |
| Retrieval & Memory | ChromaDB, LangChain                       |
| Backend            | Flask, WebSockets                         |
| Automation         | Custom Python and shell scripts           |
| Platform           | Linux Desktop                             |

---

## Setup Instructions

```bash
git clone https://github.com/Flakes342/MitchiAI.git
cd mitchi-ai

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

## Application Flow

<p align="center">
  <img width="300" height="800" src="https://github.com/user-attachments/assets/ed1a7c54-cbc7-4faf-8608-0bde1de6d1c1"
 />
</p>

