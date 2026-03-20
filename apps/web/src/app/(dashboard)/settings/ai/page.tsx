"use client";

import { useState, useCallback, useEffect } from "react";
import {
  Brain,
  Key,
  Server,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Loader2,
  Trash2,
  ExternalLink,
} from "lucide-react";
import { AppCard, AppButton, toast } from "@/components/design-system";
import {
  llmConfigApi,
  type LLMConfig,
  type LLMUsage,
  type LLMProvider,
} from "@/services/api/llm-config";
import { useAuth } from "@/contexts/AuthContext";

/* ── Provider options ────────────────────────────────────── */

const PROVIDERS: { value: LLMProvider; label: string; keyRequired: boolean }[] =
  [
    { value: "openai", label: "OpenAI", keyRequired: true },
    { value: "anthropic", label: "Anthropic", keyRequired: true },
    { value: "gemini", label: "Google Gemini", keyRequired: true },
    { value: "deepseek", label: "DeepSeek", keyRequired: true },
    { value: "mistral", label: "Mistral", keyRequired: true },
    { value: "ollama", label: "Ollama / Local AI", keyRequired: false },
  ];

/* ── Budget bar ──────────────────────────────────────────── */

function BudgetBar({ usage }: { usage: LLMUsage }) {
  const used = usage.budget?.used_usd ?? usage.estimated_cost_usd ?? 0;
  const limit = usage.budget?.limit_usd ?? 5.0;
  const pct = limit > 0 ? Math.min(100, (used / limit) * 100) : 0;
  const barColor =
    pct >= 100
      ? "var(--color-red-500)"
      : pct >= 80
        ? "var(--color-amber-500)"
        : "var(--color-green-500)";

  return (
    <div style={{ marginBlock: "0.75rem" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: "0.875rem",
          marginBottom: "0.25rem",
        }}
      >
        <span>{usage.query_count} queries this month</span>
        <span>
          ${used.toFixed(2)} of ${limit.toFixed(2)}
        </span>
      </div>
      <div
        style={{
          height: "8px",
          background: "var(--color-gray-200)",
          borderRadius: "4px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${pct}%`,
            background: barColor,
            borderRadius: "4px",
            transition: "width 0.3s",
          }}
        />
      </div>
      {pct >= 80 && pct < 100 && (
        <p
          style={{
            fontSize: "0.8rem",
            color: "var(--color-amber-600)",
            marginTop: "0.25rem",
          }}
        >
          Free allowance almost used up. Add your own API key for unlimited
          access.
        </p>
      )}
      {pct >= 100 && (
        <p
          style={{
            fontSize: "0.8rem",
            color: "var(--color-red-600)",
            marginTop: "0.25rem",
          }}
        >
          Free allowance used up this month. Add your own key or wait until it
          resets.
        </p>
      )}
    </div>
  );
}

/* ── Status badge ────────────────────────────────────────── */

function StatusBadge({ status }: { status: string }) {
  if (status === "active") {
    return (
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.25rem",
          color: "var(--color-green-600)",
          fontSize: "0.875rem",
        }}
      >
        <CheckCircle size={14} /> Active
      </span>
    );
  }
  if (status === "invalid") {
    return (
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.25rem",
          color: "var(--color-red-600)",
          fontSize: "0.875rem",
        }}
      >
        <XCircle size={14} /> Invalid — please update
      </span>
    );
  }
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.25rem",
        color: "var(--color-gray-500)",
        fontSize: "0.875rem",
      }}
    >
      <AlertTriangle size={14} /> {status}
    </span>
  );
}

/* ── Main page ───────────────────────────────────────────── */

export default function AIConfigPage() {
  const { user } = useAuth();
  const companyId = user?.company_id;

  const [config, setConfig] = useState<LLMConfig | null>(null);
  const [usage, setUsage] = useState<LLMUsage | null>(null);
  const [loading, setLoading] = useState(true);

  // BYOK form
  const [provider, setProvider] = useState<LLMProvider>("openai");
  const [apiKey, setApiKey] = useState("");
  const [modelPref, setModelPref] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [validating, setValidating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showByokForm, setShowByokForm] = useState(false);
  const [showOllamaForm, setShowOllamaForm] = useState(false);

  // Load current config
  const loadConfig = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const [cfg, usg] = await Promise.all([
        llmConfigApi.get(companyId).catch(() => null),
        llmConfigApi.getUsage(companyId).catch(() => null),
      ]);
      setConfig(cfg);
      setUsage(usg);
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  // Validate & save
  const handleSave = async () => {
    if (!companyId) return;
    const isOllama = provider === "ollama";
    const needsKey = !isOllama && !apiKey;
    const needsUrl = isOllama && !baseUrl;

    if (needsKey) {
      toast.error("Please enter an API key.");
      return;
    }
    if (needsUrl) {
      toast.error("Please enter an endpoint URL.");
      return;
    }

    // Validate first
    setValidating(true);
    try {
      const result = await llmConfigApi.validate(companyId, {
        provider,
        api_key: isOllama ? undefined : apiKey,
        base_url: isOllama ? baseUrl : undefined,
        model_pref: modelPref || undefined,
      });
      if (!result.valid) {
        toast.error(result.message || "Validation failed.");
        setValidating(false);
        return;
      }
    } catch {
      toast.error("Could not validate. Please check your input and try again.");
      setValidating(false);
      return;
    }
    setValidating(false);

    // Save
    setSaving(true);
    try {
      await llmConfigApi.save(companyId, {
        provider,
        api_key: isOllama ? undefined : apiKey,
        model_pref: modelPref || undefined,
        base_url: isOllama ? baseUrl : undefined,
      });
      toast.success(
        isOllama
          ? "Local AI service connected."
          : "API key saved and verified.",
      );
      setApiKey("");
      setShowByokForm(false);
      setShowOllamaForm(false);
      await loadConfig();
    } catch {
      toast.error("Failed to save configuration.");
    } finally {
      setSaving(false);
    }
  };

  // Delete
  const handleDelete = async () => {
    if (!companyId) return;
    if (
      !confirm(
        "Remove this AI configuration? You will switch back to the free tier.",
      )
    )
      return;
    try {
      await llmConfigApi.delete(companyId);
      toast.success("AI configuration removed.");
      setConfig(null);
      await loadConfig();
    } catch {
      toast.error("Failed to remove configuration.");
    }
  };

  if (loading) {
    return (
      <div style={{ padding: "2rem", textAlign: "center" }}>
        <Loader2
          size={24}
          className="animate-spin"
          style={{ margin: "0 auto" }}
        />
        <p style={{ marginTop: "0.5rem", color: "var(--color-gray-500)" }}>
          Loading AI settings...
        </p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: "48rem", margin: "0 auto", padding: "1.5rem" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          marginBottom: "1.5rem",
        }}
      >
        <Brain size={24} />
        <h1 style={{ fontSize: "1.5rem", fontWeight: 600 }}>
          AI Configuration
        </h1>
      </div>

      {/* ── Current Status ────────────────────────────────── */}
      <AppCard style={{ marginBottom: "1.5rem" }}>
        <h2
          style={{
            fontSize: "1.1rem",
            fontWeight: 600,
            marginBottom: "0.75rem",
          }}
        >
          Current Status
        </h2>
        {config ? (
          <div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "auto 1fr",
                gap: "0.5rem 1rem",
                fontSize: "0.9rem",
              }}
            >
              <span style={{ color: "var(--color-gray-500)" }}>Provider</span>
              <span style={{ fontWeight: 500 }}>
                {config.provider === "ollama"
                  ? "Ollama / Local AI"
                  : config.provider.charAt(0).toUpperCase() +
                    config.provider.slice(1)}{" "}
                (your key)
              </span>
              {config.masked_key && (
                <>
                  <span style={{ color: "var(--color-gray-500)" }}>
                    API Key
                  </span>
                  <span style={{ fontFamily: "monospace" }}>
                    {config.masked_key}
                  </span>
                </>
              )}
              {config.model_pref && (
                <>
                  <span style={{ color: "var(--color-gray-500)" }}>Model</span>
                  <span>{config.model_pref}</span>
                </>
              )}
              {config.base_url && (
                <>
                  <span style={{ color: "var(--color-gray-500)" }}>
                    Endpoint
                  </span>
                  <span style={{ fontFamily: "monospace" }}>
                    {config.base_url}
                  </span>
                </>
              )}
              <span style={{ color: "var(--color-gray-500)" }}>Status</span>
              <StatusBadge status={config.status} />
            </div>
            <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem" }}>
              <AppButton variant="outline" size="sm" onClick={handleDelete}>
                <Trash2 size={14} /> Remove
              </AppButton>
            </div>
          </div>
        ) : (
          <div>
            <p
              style={{ color: "var(--color-gray-600)", marginBottom: "0.5rem" }}
            >
              Using the <strong>free tier</strong> (GPT-5 mini). AI advisory
              works with a monthly allowance.
            </p>
          </div>
        )}
        {usage && <BudgetBar usage={usage} />}
      </AppCard>

      {/* ── Upgrade options (show when no BYOK config) ──── */}
      {!config && !showByokForm && !showOllamaForm && (
        <div style={{ display: "grid", gap: "1rem" }}>
          <AppCard>
            <div
              style={{ display: "flex", alignItems: "start", gap: "0.75rem" }}
            >
              <Key size={20} style={{ marginTop: "0.15rem", flexShrink: 0 }} />
              <div style={{ flex: 1 }}>
                <h3 style={{ fontWeight: 600, marginBottom: "0.25rem" }}>
                  Use your own API key
                </h3>
                <p
                  style={{
                    fontSize: "0.875rem",
                    color: "var(--color-gray-600)",
                    marginBottom: "0.75rem",
                  }}
                >
                  Unlimited queries with GPT-5 or other models. You pay the
                  provider directly.
                </p>
                <AppButton size="sm" onClick={() => setShowByokForm(true)}>
                  Enter API Key
                </AppButton>
              </div>
            </div>
          </AppCard>

          <AppCard>
            <div
              style={{ display: "flex", alignItems: "start", gap: "0.75rem" }}
            >
              <Server
                size={20}
                style={{ marginTop: "0.15rem", flexShrink: 0 }}
              />
              <div style={{ flex: 1 }}>
                <h3 style={{ fontWeight: 600, marginBottom: "0.25rem" }}>
                  Connect to a local AI service
                </h3>
                <p
                  style={{
                    fontSize: "0.875rem",
                    color: "var(--color-gray-600)",
                    marginBottom: "0.75rem",
                  }}
                >
                  Use Ollama or a shared GPU server. Unlimited queries, no cost.
                </p>
                <AppButton
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setProvider("ollama");
                    setShowOllamaForm(true);
                  }}
                >
                  Configure Endpoint
                </AppButton>
              </div>
            </div>
          </AppCard>
        </div>
      )}

      {/* ── BYOK Form ────────────────────────────────────── */}
      {showByokForm && (
        <AppCard style={{ marginTop: "1rem" }}>
          <h3 style={{ fontWeight: 600, marginBottom: "1rem" }}>
            Enter your API key
          </h3>

          <label
            style={{
              display: "block",
              fontSize: "0.875rem",
              fontWeight: 500,
              marginBottom: "0.25rem",
            }}
          >
            Provider
          </label>
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value as LLMProvider)}
            style={{
              width: "100%",
              padding: "0.5rem",
              borderRadius: "6px",
              border: "1px solid var(--color-gray-300)",
              marginBottom: "1rem",
            }}
          >
            {PROVIDERS.filter((p) => p.keyRequired).map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>

          <label
            style={{
              display: "block",
              fontSize: "0.875rem",
              fontWeight: 500,
              marginBottom: "0.25rem",
            }}
          >
            API Key
          </label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="sk-..."
            style={{
              width: "100%",
              padding: "0.5rem",
              borderRadius: "6px",
              border: "1px solid var(--color-gray-300)",
              fontFamily: "monospace",
              marginBottom: "1rem",
            }}
          />

          <label
            style={{
              display: "block",
              fontSize: "0.875rem",
              fontWeight: 500,
              marginBottom: "0.25rem",
            }}
          >
            Model{" "}
            <span style={{ fontWeight: 400, color: "var(--color-gray-400)" }}>
              (optional)
            </span>
          </label>
          <input
            type="text"
            value={modelPref}
            onChange={(e) => setModelPref(e.target.value)}
            placeholder="gpt-5-chat-latest"
            style={{
              width: "100%",
              padding: "0.5rem",
              borderRadius: "6px",
              border: "1px solid var(--color-gray-300)",
              marginBottom: "1rem",
            }}
          />

          <div
            style={{
              fontSize: "0.8rem",
              color: "var(--color-gray-500)",
              marginBottom: "1rem",
            }}
          >
            Your key is encrypted and stored securely. Only company admins can
            view or change it.
            {provider === "openai" && (
              <>
                {" "}
                Get a key at{" "}
                <a
                  href="https://platform.openai.com/api-keys"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: "var(--color-blue-600)" }}
                >
                  platform.openai.com{" "}
                  <ExternalLink size={11} style={{ display: "inline" }} />
                </a>
              </>
            )}
          </div>

          <div style={{ display: "flex", gap: "0.5rem" }}>
            <AppButton onClick={handleSave} disabled={validating || saving}>
              {validating ? (
                <>
                  <Loader2 size={14} className="animate-spin" /> Validating...
                </>
              ) : saving ? (
                <>
                  <Loader2 size={14} className="animate-spin" /> Saving...
                </>
              ) : (
                "Validate & Save"
              )}
            </AppButton>
            <AppButton
              variant="outline"
              onClick={() => {
                setShowByokForm(false);
                setApiKey("");
              }}
            >
              Cancel
            </AppButton>
          </div>
        </AppCard>
      )}

      {/* ── Ollama Form ──────────────────────────────────── */}
      {showOllamaForm && (
        <AppCard style={{ marginTop: "1rem" }}>
          <h3 style={{ fontWeight: 600, marginBottom: "1rem" }}>
            Connect to local AI service
          </h3>

          <label
            style={{
              display: "block",
              fontSize: "0.875rem",
              fontWeight: 500,
              marginBottom: "0.25rem",
            }}
          >
            Endpoint URL
          </label>
          <input
            type="text"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="http://localhost:11434"
            style={{
              width: "100%",
              padding: "0.5rem",
              borderRadius: "6px",
              border: "1px solid var(--color-gray-300)",
              fontFamily: "monospace",
              marginBottom: "1rem",
            }}
          />

          <label
            style={{
              display: "block",
              fontSize: "0.875rem",
              fontWeight: 500,
              marginBottom: "0.25rem",
            }}
          >
            Model{" "}
            <span style={{ fontWeight: 400, color: "var(--color-gray-400)" }}>
              (optional — auto-detected if empty)
            </span>
          </label>
          <input
            type="text"
            value={modelPref}
            onChange={(e) => setModelPref(e.target.value)}
            placeholder="llama3.1:70b"
            style={{
              width: "100%",
              padding: "0.5rem",
              borderRadius: "6px",
              border: "1px solid var(--color-gray-300)",
              marginBottom: "1rem",
            }}
          />

          <div
            style={{
              fontSize: "0.8rem",
              color: "var(--color-gray-500)",
              marginBottom: "1rem",
            }}
          >
            Works with Ollama or any Ollama-compatible service (including NVIDIA
            DGX). No API key needed.
          </div>

          <div style={{ display: "flex", gap: "0.5rem" }}>
            <AppButton onClick={handleSave} disabled={validating || saving}>
              {validating ? (
                <>
                  <Loader2 size={14} className="animate-spin" /> Testing...
                </>
              ) : saving ? (
                <>
                  <Loader2 size={14} className="animate-spin" /> Saving...
                </>
              ) : (
                "Test & Save"
              )}
            </AppButton>
            <AppButton
              variant="outline"
              onClick={() => {
                setShowOllamaForm(false);
                setBaseUrl("");
              }}
            >
              Cancel
            </AppButton>
          </div>
        </AppCard>
      )}
    </div>
  );
}
