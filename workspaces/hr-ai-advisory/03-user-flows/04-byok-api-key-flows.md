# User Flows: BYOK API Keys + Budget-Capped Default

## Flow 1: First-Time User — AI Works Immediately

```
User signs up, company created
  → Admin visits AI Advisory
  → Advisory works immediately (server key, gpt-5-mini)
  → User asks: "How many days of annual leave must I give?"
  → Gets answer with citations
  → Small usage indicator: "3 of ~500 free queries this month"
```

No setup needed. The server key handles it. Budget tracked silently.

## Flow 2: Admin Views AI Settings

```
Admin navigates to Settings > AI Configuration
  → Shows current status:
    ┌─────────────────────────────────────────────────────────┐
    │  AI Configuration                                       │
    │                                                         │
    │  Current: Free tier (gpt-5-mini)                        │
    │  Usage this month: 47 queries · $0.52 of $5.00          │
    │  ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  10%       │
    │                                                         │
    │  ┌──────────────────────────────────────────┐           │
    │  │  Use your own OpenAI key                 │           │
    │  │                                          │           │
    │  │  Unlimited queries with GPT-5.           │           │
    │  │  You pay OpenAI directly.                │           │
    │  │                                          │           │
    │  │  [Enter API Key]                         │           │
    │  └──────────────────────────────────────────┘           │
    │                                                         │
    │  ┌──────────────────────────────────────────┐           │
    │  │  Connect to a local AI service           │           │
    │  │                                          │           │
    │  │  Use Ollama or a shared GPU server.      │           │
    │  │  Unlimited queries, no cost.             │           │
    │  │                                          │           │
    │  │  [Configure Endpoint]                    │           │
    │  └──────────────────────────────────────────┘           │
    └─────────────────────────────────────────────────────────┘
```

## Flow 3: Admin Enters BYOK Key

```
Admin clicks "Enter API Key"
  → Form appears:
    ┌─────────────────────────────────────────────────────────┐
    │  Your OpenAI API Key                                    │
    │                                                         │
    │  API Key:  [sk-________________________________]        │
    │                                                         │
    │  Get a key at platform.openai.com/api-keys              │
    │                                                         │
    │  [Validate & Save]                                      │
    │                                                         │
    │  Your key is encrypted and stored securely.             │
    │  Only company admins can see or change it.              │
    │  AI advisory will use GPT-5 (gpt-5-chat-latest).       │
    └─────────────────────────────────────────────────────────┘

  → Admin pastes key, clicks "Validate & Save"
  → Backend: sends minimal completion to verify key works
  → Success:
    ┌─────────────────────────────────────────────────────────┐
    │  AI Configuration                                  ✓    │
    │                                                         │
    │  Provider:  OpenAI (your key)                           │
    │  API Key:   sk-...a1b2                                  │
    │  Model:     GPT-5 (gpt-5-chat-latest)                   │
    │  Status:    Active ✓                                    │
    │  Limit:     Unlimited                                   │
    │                                                         │
    │  [Change Key]  [Remove Key]                             │
    └─────────────────────────────────────────────────────────┘
```

## Flow 4: Admin Configures Ollama / DGX

```
Admin clicks "Configure Endpoint"
  → Form appears:
    ┌─────────────────────────────────────────────────────────┐
    │  Local AI Service (Ollama)                              │
    │                                                         │
    │  Endpoint:  [http://dgx.institution.edu:11434_]         │
    │  Model:     [llama3.1:70b____________________]          │
    │                                                         │
    │  [Test Connection]                                      │
    │                                                         │
    │  Works with Ollama, or any Ollama-compatible service.   │
    │  No API key needed. Unlimited queries.                  │
    └─────────────────────────────────────────────────────────┘

  → Admin enters endpoint and model, clicks "Test Connection"
  → Backend: hits /api/tags on the endpoint, verifies model exists
  → Success:
    ┌─────────────────────────────────────────────────────────┐
    │  AI Configuration                                  ✓    │
    │                                                         │
    │  Provider:  Ollama (dgx.institution.edu)                │
    │  Model:     llama3.1:70b                                │
    │  Status:    Connected ✓                                 │
    │  Limit:     Unlimited                                   │
    │                                                         │
    │  [Change Settings]  [Remove]                            │
    └─────────────────────────────────────────────────────────┘
```

## Flow 5: Budget Warning + Exceeded

```
Company approaching $5 cap (80% = $4.00):
  → User asks a question
  → Gets answer normally
  → Warning banner at bottom of response:
    "Your company's free AI allowance is almost used up this month.
     Ask your admin to add an API key for unlimited access."

Company at $5 cap (100%):
  → User asks a question
  → No LLM call made
  → Friendly message:
    ┌─────────────────────────────────────────────────────────┐
    │  Free AI allowance used up                              │
    │                                                         │
    │  Your company has used its free AI queries for this     │
    │  month. It resets on the 1st.                           │
    │                                                         │
    │  To get unlimited access:                               │
    │  • Add your own OpenAI key in Settings                  │
    │  • Or connect to a local AI service                     │
    │                                                         │
    │  All other features (payroll, leave, claims, etc.)      │
    │  continue to work normally.                             │
    └─────────────────────────────────────────────────────────┘

  If user is admin → show "Go to Settings" button
  If user is employee → show "Ask your admin" message
```

## Flow 6: Employee Experience (Non-Admin)

```
Employee opens AI Advisory
  → System resolves company's AI config
  → Chat works normally — employee never sees config details
  → Subtle footer: "AI powered by GPT-5 mini" or "AI powered by Ollama"

  If company has BYOK key:
  → Footer: "AI powered by GPT-5"
  → No budget limit

  If no AI configured and no server key:
  → "AI advisory isn't available yet. Ask your company admin."
```

## Flow 7: Provider Resolution (Backend)

```
Advisory request for company_id=42:

  Step 1: Check CompanyLLMConfig for company_id=42
    → BYOK key (status="active")?
      YES → Decrypt key, use gpt-5-chat-latest. No budget check. DONE.
    → Ollama endpoint (status="active")?
      YES → Use endpoint + model. No budget check. DONE.
    → Neither? Continue...

  Step 2: Check server config
    → OPENAI_API_KEY in .env?
      YES → Check budget:
        → CompanyLLMUsage.estimated_cost < $5.00?
          YES → Use server key + gpt-5-mini. DONE.
          NO → Return budget_exceeded. DONE.
    → No server key? Continue...

  Step 3: Auto-detect Ollama on localhost
    → Running? Use it. DONE.

  Step 4: No LLM available
    → Return { "llm_available": false }
```

## Flow 8: Key Becomes Invalid

```
Advisory request → decrypt BYOK key → call OpenAI → 401 response
  → Mark CompanyLLMConfig status = "invalid"
  → Fall back to server key (budget permitting)
  → Response includes warning:
    "Note: Your API key is no longer valid.
     This response used the free tier instead.
     Update your key in Settings."

Admin visits Settings:
  → Status shows: "Key Invalid — please update"
  → [Enter New Key] button prominent
```

## Edge Cases

### Company switches from BYOK back to default

- Admin clicks "Remove Key"
- Confirmation: "AI advisory will use the free tier ($5/month limit)."
- Key hard-deleted from DB
- Budget tracking resumes for remaining month

### Multiple admins

- Any admin can set/change the key
- `updated_by` tracks who last changed it
- Old key overwritten (one key per company)

### Ollama endpoint goes down

- Advisory call times out
- Fall back to server key (budget permitting)
- Show: "The local AI service is unreachable. Using the free tier instead."

### Mid-month BYOK addition

- Company used $3.20 on free tier, admin adds BYOK key
- All subsequent queries use BYOK (no budget check)
- Budget counter stops incrementing (only counts server-key usage)
- If admin removes BYOK later, remaining $1.80 of budget is still available
