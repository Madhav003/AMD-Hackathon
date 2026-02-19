# 🛡️ Promptshield (Title Pending)

### Campus LLM Privacy & Prompt Injection Defense System

> A lightweight AI security proxy that protects students and faculty from leaking sensitive data and falling victim to prompt injection attacks.

---

# 🚩 Problem Statement

Students and faculty frequently paste:

* Research data
* Private source code
* Financial information
* Personally Identifiable Information (PII)

into public LLM tools like ChatGPT.

Additionally, modern AI systems are vulnerable to:

* **Indirect Prompt Injections**
* **Jailbreak attempts**
* **System prompt extraction**
* **AI recommendation poisoning**

This creates institutional risk, data leaks, and reputational damage.

---

# 💡 Our Solution

PromptShield is a **secure API gateway** that acts as a protective layer between users and Large Language Models.

### Instead of:

User → Gemini API

### We implement:

User → PromptShield Gateway → Security Filtering → Gemini API

---

# 🔒 Core Security Features

## 1️⃣ PII Scrubbing Engine

* Detects emails, phone numbers, credit cards, SSNs
* Masks sensitive content
* Optionally logs anonymized detection metrics

Example:

```
Input:  My email is john@example.com
Output: My email is [REDACTED_EMAIL]
```

---

## 2️⃣ Prompt Injection Detection

Blocks known malicious patterns such as:

* "Ignore previous instructions"
* "Reveal system prompt"
* "You are DAN"
* Attempts to override system behavior
* Instruction escalation attempts

If detected:

* Request is blocked OR sanitized
* Logged for analysis

---

## 3️⃣ Lightweight Proxy Architecture

* Hosted on AWS EC2
* Built using FastAPI
* Secure forwarding to Gemini API
* Modular security filtering layer

---

# 🧠 Why This Project Wins

* Directly addresses **OWASP Top 10 for LLMs**
* Protects institutional trust
* Extremely relevant in academic environments
* Real-world deployable
* High research potential

This can evolve into:

* A research paper analyzing prompt injection frequency
* An enterprise AI firewall
* A campus-wide AI gateway solution

---

# 🏗️ Architecture Overview

```
[ Streamlit UI ]
        ↓
[ FastAPI Backend ]
        ↓
[ Security Layer ]
   • Regex PII Detection
   • Prompt Injection Blocklist
   • (Optional) Microsoft Presidio
        ↓
[ Gemini API ]
        ↓
[ Response returned to User ]
```

---

# 🧩 Tech Stack

### Backend

* Python
* FastAPI
* Gemini Python SDK

### Security Layer

* Python `re` (Regex)
* Custom blocklist logic
* Optional: Microsoft Presidio

### Frontend

* Streamlit (Chat Interface)

### Deployment

* AWS EC2 (Ubuntu instance)
* Public IP hosting
* Security Groups configuration

---

# 👥 Team Roles & Responsibilities

---

## 🔹 API & Backend Architects

**Madhav, Mahir**

### Responsibilities:

* Build FastAPI server
* Create `/ask` endpoint
* Integrate Security script
* Forward sanitized prompt to Gemini
* Return LLM response to frontend
* Manage async request flow

### Key Concepts:

* REST APIs
* JSON handling
* Async/Await basics
* API authentication

---

## 🔹 Security & NLP Engineers

**Dhruvi, Madhav, Mahir**

### Responsibilities:

* Implement PII masking logic
* Build Regex-based detection patterns
* Maintain injection keyword blocklist
* Research OWASP LLM vulnerabilities
* Improve detection accuracy
* Prevent jailbreak attempts

### Core Security Objectives:

* Mask PII without breaking prompt meaning
* Detect malicious prompt patterns
* Minimize false positives
* Keep filtering lightweight and fast

---

## 🔹 Frontend & Cloud Deployment

**Dhruvi, Mahir**

### Responsibilities:

* Build Streamlit chat interface
* Connect UI to FastAPI endpoint
* Deploy system to AWS EC2
* Configure security groups
* Handle SSH + server setup
* Ensure public accessibility

### Deployment Goals:

* Stable EC2 hosting
* Open required ports (80 / 8000)
* Secure API key handling
* Clean demo-ready interface

---

# 🎯 Current Objectives (Dev Branch)

This branch represents **active development**.

### 🔧 Backend

* [ ] FastAPI server running locally
* [ ] `/ask` endpoint implemented
* [ ] Gemini API integration working
* [ ] Proper error handling added

### 🔒 Security

* [ ] Email detection regex
* [ ] Phone number detection
* [ ] Credit card detection
* [ ] SSN detection
* [ ] Injection blocklist implementation
* [ ] Logging for flagged prompts
* [ ] Optional Presidio integration

### 🖥 Frontend

* [ ] Streamlit chat UI
* [ ] Input box + message history
* [ ] Loading state indicator
* [ ] API integration

### ☁ Deployment

* [ ] EC2 instance launched
* [ ] Security groups configured
* [ ] App accessible via public IP
* [ ] Environment variables secured

---

# 🧪 Testing Strategy

We must test with:

* Normal academic prompts
* Prompts containing emails
* Prompts containing credit card numbers
* Known jailbreak attempts
* Edge cases (very long prompts)

System must:

* Not crash
* Not leak PII
* Not allow instruction override

---

# 📊 Future Research Potential

* Prompt injection frequency analysis
* Dataset of academic AI attack attempts
* AI Recommendation Poisoning detection
* Defensive AI gateway benchmarking

---

# ⚠️ Development Rules

* Do NOT commit API keys
* Use `.env` file (ignored in `.gitignore`)
* Never push directly to `main`
* All development happens in `dev`
* Write clear commit messages

---

# 🔐 Security Philosophy

We are not trying to build a perfect AI firewall.

We are building:

* A practical
* Fast
* Lightweight
* Deployable
* Research-backed

AI security gateway for academic environments.

---