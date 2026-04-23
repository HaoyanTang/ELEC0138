# ELEC0138 Smart Lock Security Project

This project implements a prototype smart door lock system for the ELEC0138 Security and Privacy coursework. It includes a vulnerable version，a partly secured version (no HTTPS), and a fully secured version to demonstrate common IoT security threats and corresponding defense mechanisms.

## Project Overview

The system consists of three main components:

- Frontend application built with Streamlit
- Backend server built with FastAPI
- Simulated IoT smart lock service

The project demonstrates attacks such as packet sniffing, unauthorized API access, and replay attacks. It also implements security mechanisms including HTTPS, JWT-based authentication, HMAC message authentication, and timestamp validation.

## Project Structure

```text
ELEC0138/
├── vuln/
│   ├── backend_vuln/
│   ├── frontend_vuln/
│   ├── lock_vuln/
│   └── attacks/
│
├── secured/
│   ├── backend/
│   ├── frontend/
│   ├── lock/
│   └── attacks/
│
├── secured_demo_replayattack/
│   ├── backend/
│   ├── frontend/
│   ├── lock/
│   └── attacks/
│
└── README.md
```

## Environment Setup

```bash
pip install -r requirements.txt
```

## How To Run

### Vuln

Open three terminals

```bash
python vuln/lock_vuln/lock_vuln.py
python vuln/backend_vuln/backend_vuln.py
streamlit run vuln/frontend_vuln/frontend_vuln.py
```

### Fully Secured

Open three terminals

```bash
python secured/lock/lock.py
python secured/backend/backend.py
streamlit run secured/frontend/frontend.py
```

### Partly Secured

Open three terminals

```bash
python secured_demo_replayattack/lock/lock.py
python secured_demo_replayattack/backend/backend.py
streamlit run secured_demo_replayattack/frontend/frontend.py
```

## How to Use the Frontend
1. Register
Create a new account.

2. Login
Login to receive a JWT token.

3. Pair Lock
Enter lock ID + password.(1, 88888888)

4. Control Lock
Click button to toggle lock state.

## How to simulate attack

### Vuln

Open three terminals

```bash
python vuln/attacks/API_abuse.py
python vuln/attacks/replayattack.py
```

### Fully Secured

Open three terminals

```bash
python secured/attacks/API_abuse.py
```

### Partly Secured

Open three terminals

```bash
python secured_demo_replayattack/attacks/replayattack.py
python secured_demo_replayattack/attacks/forgeattack
```
